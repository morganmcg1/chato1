from fasthtml.common import *

from fastlite import *

from prompt_models import (
    PROMPT_GEN_SYSTEM_PROMPT,
    PROMPT_GEN_PROMPT,
    PromptModel,
    call_llm,
    call_dummy_llm
)

import os
import html
import json
import uuid
from datetime import datetime
import logging

import asyncio

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set the environment variable before starting the server
os.environ['WATCHFILES_IGNORE_REGEXES'] = r'.*\.db$ .*\.db-journal$'

db = Database('prompt_battle2.db')

class Generation: 
    call_id: str;
    session_id: str;
    call_type: str;
    input:str; 
    output: str; 
    timestamp: datetime;

generations_tbl = db.create(Generation, pk='call_id', transform=True)

app, rt = fast_app(
    pico=False, # Disable Pico.css to prevent style conflicts
    hdrs=(
        Link(rel='stylesheet', href='https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap'),
        Script(src="https://unpkg.com/htmx.org@1.9.2"),
        Script(src="https://unpkg.com/htmx-ext-sse@2.2.1/sse.js")  # SSE for server-sent events
    )
)  

style = Style("""
    *, *::before, *::after {
        box-sizing: border-box;
    }
    h1, .btn, .grading-thank-you-container,submit-button, input-form {
        font-family: 'Poppins', sans-serif;
    }
    body {
        background-color: white;
        color: black;
        margin: 0;
    }
    h1 {
        color: black;
    }
    .submit-button {
        background-color: yellow;
        padding: 5px 10px;
        flex: none;
    }
    .input-form {
        display: flex;
        align-items: center;
        padding: 0 20px;
    }
    .input-form input[name="user_input"] {
        flex: 1;
        margin-right: 10px;
        padding: 5px;
    }
    main {
        padding: 0 20px 100px 20px;
    }
    .output-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
    }
    .output-box {
        width: 48%;
        margin-bottom: 10px;
        display: inline-block;
        vertical-align: top;
        height: 300px;
        border: 1px solid #ccc;
        padding: 10px;
        overflow: auto;
        word-wrap: break-word;
        flex-shrink: 0;
    }
    .notes-input {
        width: 100%;
        padding: 5px;
        margin-bottom: 5px;
        border: 1px solid #ccc;
        border-radius: 3px;
    }
    .notes-container {
        margin-bottom: 10px;
    }
    .grading-container {
        margin-top: 20px;
        text-align: center;
    }
    .grading-form .button-group {
        display: inline-block;
    }
    .grading-message {
        margin-top: 10px;
        color: green;
    }
    .buttons {
        display: flex;
        flex-direction: column;
        align-items: stretch;
        flex: 1 1 48%;
        min-width: 300px;
        margin-bottom: 10px;
    }
    .button-container {
        margin-top: 10px;
    }
               /* Button styles */
    .btn {
        padding: 5px 10px;
        border: none;
        cursor: pointer;
        margin-right: 5px;
    }
    .btn-success {
        background-color: #4CAF50;
        color: white;
    }
    .btn-error {
        background-color: #f44336;
        color: white;
    }
    .btn:hover {
        opacity: 0.5;
    }
    /* Responsive adjustments */
    @media (max-width: 800px) {
        .output-box, .buttons {
            width: 100%;
            display: block;
        }
    }
""")

submission_form_placeholder = "Please enter a task"

@rt('/')
def get():
    return Titled(
        "Prompt Battle",
        style,
        H2("Welcome to Prompt Battle"),
        Main(
            Div(
                Div(
                    create_output_box('output-box1'),
                    create_output_box('output-box2'),
                    cls='output-container'
                ),
                Div(
                    create_output_box_with_trigger('output-box3'),
                    create_output_box_with_trigger('output-box4'),
                    cls='output-container'
                ),
                Div(
                    create_grading_buttons(),
                    cls='grading-container'
                ),
                create_polling_trigger_div()
            ),
        ),
        Div(
            create_submission_form(),
            style='position: fixed; bottom: 20px; left: 0; right: 0; background: #fff; padding: 10px 20px;'
        ),
    )

def create_submission_form():
    return Form(
        Div(
            Input(
                type='text', 
                name='user_input', 
                id='user-input',
                placeholder=submission_form_placeholder
            ),
            Button(
                'Submit',
                type='submit', 
                cls='submit-button'
            ),
            cls='input-form'
        ),
        method='post',
        hx_post='/output',
        hx_swap='none',
        style='margin: 0;'
    )

def create_output_box(box_id):
    return Div(
        Div(id=f'{box_id}-content', cls='output-content'),
        id=box_id,
        cls='output-box',
    )

def create_polling_trigger_div():
    return Div(
        '',
        id='generations-polling-trigger',
        style='display: none;',
    )

def create_grading_buttons():
    return Div(
        Form(
            Button(
                "Output 1",
                type="submit",
                name="grade",
                value="output-1",
                cls="btn btn-success mr-2",
            ),
            Button(
                "Output 2",
                type="submit",
                name="grade",
                value="output-2",
                cls="btn btn-success mr-2",
            ),
            Button(
                "Tie",
                type="submit",
                name="grade",
                value="tie",
                cls="btn btn-success mr-2",
            ),
            method="post",
            hx_post=f"/grade_output",
            # hx_target="this",
            hx_target="#grading-message",
            hx_swap="innerHTML",
            # hx_swap="outerHTML",
            cls="grading-form",
        ),
        Div(
            id="grading-message",
            cls="grading-message-container",
        ),
        cls='button-container',
    )


def create_output_box_with_trigger(box_id):
    return Div(
        Div(
            id=f'{box_id}-content',
            cls='output-content',
            # hx_trigger='outputs1and2Loaded from:window',
            # hx_get='/process_additional_outputs',
            # hx_vals='js:event.detail',
        ),
        id=box_id,
        cls='output-box',
    )

@rt('/grade_output', methods=['POST'])
def grade_output(grade: str, session):
    o1_output = session.get('o1_prompt_json', '')
    challenger_output = session.get('challenger_prompt_json', '')

    grade_entry = {
        'grade': grade,
        'output_1': o1_output,
        'output_2': challenger_output,
        'timestamp': datetime.now().isoformat(),
    }

    session.setdefault('latest_grade', {})
    session['latest_grade'] = grade_entry

    session.setdefault('grade_list', [])
    session['grade_list'].append(grade_entry)

    logger.debug(f"Grade received: {grade_entry}")

    return Div(
        P("Thanks, grade received!"),
        cls='grading-thank-you-container',
    )


# @threaded
# def threaded_call_dummy_llm(
#     system_prompt: str,
#     user_prompt: str,
#     model_name: str,
#     response_model: PromptModel,
#     sleep_time: float = 0,
# ):
#     return call_dummy_llm(
#         system_prompt=system_prompt,
#         user_prompt=user_prompt,
#         model_name=model_name,
#         response_model=response_model,
#         sleep_time=sleep_time
#     )

# @rt('/output', methods=['POST'])
# def output(user_input: str, session):

#     o1_prompt = call_dummy_llm(
#         user_prompt=user_input,
#         model_name="gpt-4o-mini",
#         response_model=PromptModel,
#         sleep_time=1.5
#     )
#     o1_prompt_json = o1_prompt.model_dump_json()
#     o1_prompt_json = o1_prompt.user_prompt
#     logger.debug(f"o1_prompt_json: {o1_prompt_json}")

#     challenger_prompt = call_dummy_llm(
#         system_prompt=PROMPT_GEN_SYSTEM_PROMPT,
#         user_prompt=user_input,
#         model_name="gpt-4o-mini",
#         response_model=PromptModel
#     )
#     challenger_prompt_json = challenger_prompt.model_dump_json()
#     challenger_prompt_json = challenger_prompt.user_prompt
#     logger.debug(f"challenger_prompt_json: {challenger_prompt_json}")

#     session['o1_prompt_json'] = o1_prompt_json
#     session['challenger_prompt_json'] = challenger_prompt_json
    
#     # Build the content to return as a list of Divs so that both outputs can be returned
#     content = ''.join([
#         Div(
#             P(o1_prompt_json),
#             id='output-box1-content',
#             hx_swap_oob='true',
#         ).__html__(),  # Convert to HTML string
#         Div(
#             P(challenger_prompt_json),
#             id='output-box2-content',
#             hx_swap_oob='true',
#         ).__html__(),
#     ])

#     # Create a new empty input field to clear the existing one
#     clear_input = Input(
#         type='text',
#         name='user_input',
#         id='user-input',        # Same ID as the original input field
#         placeholder=submission_form_placeholder,
#         hx_swap_oob='true'      # Perform out-of-band swap
#     )

#     # Create the response with the HX-Trigger header
#     response = HTMLResponse(content=content + clear_input.__html__())
#     response.headers['HX-Trigger'] = 'outputs1and2Loaded'
#     logger.debug(f"response: {response}")
#     return response

# @rt("/generations/{call_id}", methods=['GET'])
# def get(call_id: str, request):
#     # call_id = request.query_params.get('call_id')
#     # if not call_id:
#     #     return HTMLResponse("Missing call_id", status_code=400)
#     logger.debug(f"get generations/ called with call_id: {call_id}")
#     return generation_preview(call_id)

@rt("/check_generations", methods=['GET'])
def get_generations(request):
    call_id = request.query_params.get('call_id')
    if not call_id:
        return HTMLResponse("Missing call_id in get_generations", status_code=400)
    logger.debug(f"get generations called with call_id: {call_id}")
    return display_generations(call_id)



def display_generations(call_id):
    # check if there is a generation for call_id in the db yet
    try:
        logger.debug(f"Trying to get generation: {call_id}-o1_prompt")
        o1_prompt = generations_tbl[f"{call_id}-o1_prompt"]
        prompt_gen_complete = True
    except:
        prompt_gen_complete = False

    try:
        logger.debug(f"Trying to get final output: {call_id}-o1_output")
        o1_output_gen = generations_tbl[f"{call_id}-o1_output"]
        output_gen_complete = True
    except:
        output_gen_complete = False

    if output_gen_complete:
        challenger_output = generations_tbl[f"{call_id}-challenger_output"]
        
        o1_output_json = o1_output_gen.output
        challenger_output_json = challenger_output.output

        logger.debug(f"WE HAVE A GENERATION! Triggering further processing")
        
        # Build the content to return as a list of Divs so that both outputs can be returned
        content = ''.join([
            # Update output-box3-content with call_id in hx_get
            Div(
                P(o1_output_json),
                id='output-box3-content',
                cls='output-content',
                hx_swap='innerHTML',
                hx_swap_oob='true',
            ).__html__(),
            # Update output-box4-content with call_id in hx_get
            Div(
                P(challenger_output_json),
                id='output-box4-content',
                cls='output-content',
                hx_swap='innerHTML',
                hx_swap_oob='true',

            ).__html__(),
            # Stop polling
            Div(
                '',
                id='generations-polling-trigger',
                hx_swap='innerHTML', 
                hx_swap_oob='true',
                style='display: hidden;',  
            ).__html__(),
        ])
        # Create the response with the HX-Trigger header
        response = HTMLResponse(content=content + clear_submission_input().__html__())
        return response
    
    elif prompt_gen_complete:
        o1_prompt_json = o1_prompt.output

        challenger_gen = generations_tbl[f"{call_id}-challenger_prompt"]
        challenger_prompt_json = challenger_gen.output

        logger.debug(f"WE HAVE A GENERATION! Triggering further processing")
        
        # Build the content to return as a list of Divs so that both outputs can be returned
        content = ''.join([
            Div(
                P(o1_prompt_json),
                id='output-box1-content',
                hx_swap_oob='true',
            ).__html__(),
            Div(
                P(challenger_prompt_json),
                id='output-box2-content',
                hx_swap_oob='true',
            ).__html__(),
            # Update output-box3-content with call_id in hx_get
            Div(
                P("Generating..."),
                id='output-box3-content',
                cls='output-content',
                hx_swap='innerHTML',
                hx_swap_oob='true',
            ).__html__(),
            # Update output-box4-content with call_id in hx_get
            Div(
                P("Generating..."),
                id='output-box4-content',
                cls='output-content',
                hx_swap='innerHTML',
                hx_swap_oob='true',

            ).__html__(),
            # polling route for final outputs
            Div(
                '',
                id='generations-polling-trigger',
                hx_trigger='every 500ms',
                hx_get=f"/check_generations?call_id={call_id}",
                hx_swap='innerHTML', 
                hx_swap_oob='true',
                style='display: hidden;',  
            ).__html__(),
        ])
        # Create the response with the HX-Trigger header
        response = HTMLResponse(content=content + clear_submission_input().__html__())
        return response
    
    else:
        content = ''.join([
            Div(
                P("Generating..."),
                id='output-box1-content',
                # hx_get=f"/generations?call_id={call_id}",
                hx_swap='innerHTML',  # just update the content, not the entire box
                hx_swap_oob='true',
                # hx_trigger='every 200ms',
            ).__html__(), 
            Div(
                P("Generating..."),
                id='output-box2-content',
                hx_swap='innerHTML', 
                hx_swap_oob='true',
            ).__html__(),
            Div(
                P("Queued..."),
                id='output-box3-content',
                hx_swap='innerHTML',  # just update the content, not the entire box
                hx_swap_oob='true',
            ).__html__(), 
            Div(
                P("Queued..."),
                id='output-box4-content',
                hx_swap='innerHTML', 
                hx_swap_oob='true',
            ).__html__(),
            # Hidden element with the polling trigger
            Div(
                '',
                id='generations-polling-trigger',
                hx_trigger='every 500ms',
                hx_get=f"/generations?call_id={call_id}",
                hx_swap='innerHTML', 
                hx_swap_oob='true',
                style='display: hidden;',  
            ).__html__(),
        ])

        # Create the response with the HX-Trigger header
        response = HTMLResponse(content=content + clear_submission_input().__html__())
        logger.debug(f"response: {response}")
        return response
    
# def test_return(id):
#     content = ''.join([
#         Div(
#             P("Generating..."),
#             id='output-box1-content',
#             hx_swap_oob='true',
#         ).__html__(), 
#         Div(
#             P("Generating..."),
#             id='output-box2-content',
#             hx_swap_oob='true',
#         ).__html__(),
#     ])
#     response = HTMLResponse(content=content + clear_submission_input().__html__())
#     return response



@threaded
def generate_candidate_prompts(user_input: str, session, call_id: str):
# async def generate_candidate_prompts(user_input: str, session, call_id: str):
    
    logger.debug(f"Getting first outputs for: {user_input}")
    o1_prompt = call_dummy_llm(
        user_prompt=user_input,
        model_name="gpt-4o-mini",
        response_model=PromptModel,
        sleep_time=2
    )
    o1_prompt_json = o1_prompt.model_dump_json()
    o1_prompt_json = o1_prompt.user_prompt
    logger.debug(f"o1_prompt_json: {o1_prompt_json}")

    challenger_prompt = call_dummy_llm(
        system_prompt=PROMPT_GEN_SYSTEM_PROMPT,
        user_prompt=user_input,
        model_name="gpt-4o-mini",
        response_model=PromptModel
    )
    challenger_prompt_json = challenger_prompt.model_dump_json()
    challenger_prompt_json = challenger_prompt.user_prompt
    logger.debug(f"challenger_prompt_json: {challenger_prompt_json}")

    # insert the generation into the database
    session_id = session.get("session_id")

    logger.debug(f"Inserting generation into database: {call_id}-o1_prompt:\n{o1_prompt_json}")
    generations_tbl.insert(Generation(
        call_id=call_id + '-o1_prompt',
        session_id=session_id,
        call_type='o1_prompt',
        input=user_input, 
        output=o1_prompt_json, 
        timestamp=datetime.now().isoformat()
    ))

    logger.debug(f"Inserting generation into database: {call_id}-challenger_prompt:\n{challenger_prompt_json}")
    generations_tbl.insert(Generation(
        call_id=call_id + '-challenger_prompt',
        session_id=session_id,
        call_type='challenger_prompt',
        input=user_input, 
        output=challenger_prompt_json, 
        timestamp=datetime.now().isoformat()
    ))
    return o1_prompt_json, challenger_prompt_json

def clear_submission_input():
    # Create a new empty input field to clear the existing one
    return Input(
        type='text',
        name='user_input',
        id='user-input',        # Same ID as the original input field
        placeholder=submission_form_placeholder,
        hx_swap_oob='true'      # Perform out-of-band swap
    )

# async def run_generation_pipeline(user_input: str, session, call_id: str):
    
#     o1_prompt_json, challenger_prompt_json = await generate_candidate_prompts(user_input, session, call_id)
    
#     o1_output, challenger_output = await process_additional_outputs(o1_prompt_json, challenger_prompt_json, session, call_id)
    
#    # Store outputs using 'call_id' as the key
#     logger.debug(f"Storing outputs for call_id: {call_id} in the session variable")
#     session['outputs'][call_id] = {
#         'o1_output': o1_output,
#         'challenger_output': challenger_output
#     }

#     logger.debug(f"Session updated, session: {session}")

#     return o1_output, challenger_output



# SSE endpoint for o1_output
@rt('/sse_output_monitor/{output_name}')
async def sse_output(session, call_id: str, output_name: str):
    async def output_generator():
        while True:
            logger.debug(f"In SSE monitor for {output_name}, call_id: {call_id}, session: {session}")
            outputs = session.get('outputs', {}).get(call_id, {})
            logger.debug(f"In SSE monitor searching for {output_name} in outputs: {outputs}")
            if output_name in outputs:
                logger.debug(f"Sending SSE message for {output_name}: {outputs[output_name]}")
                yield sse_message(P(outputs[output_name]), event=f'{output_name}_event')
                # Clean up after sending
                del session['outputs'][call_id][output_name]
                if not session['outputs'][call_id]:
                    del session['outputs'][call_id]
                break
            await asyncio.sleep(5)  # TODO drop sleep time again
    return EventStream(output_generator())


# def simple_generation_preview(call_id):
#     logger.debug(f"In simple_generation_preview for call_id: {call_id}")
#     content = ''.join([
#         Div(
#             P("Generating..."),
#             id='output-box1-content',
#             # hx_get=f"/generations?call_id={call_id}",
#             hx_swap='innerHTML',  # just update the content, not the entire box
#             hx_swap_oob='true',
#             # hx_trigger='every 200ms',
#         ).__html__(), 
#         Div(
#             P("Generating..."),
#             id='output-box2-content',
#             # hx_get=f"/generations?call_id={call_id}",
#             hx_swap='innerHTML', 
#             hx_swap_oob='true',
#             # hx_trigger='every 200ms',  # poll every 1 second
#         ).__html__(),
#         Div(
#             P("Generating..."),
#             id='output-box3-content',
#             hx_swap='innerHTML',  # just update the content, not the entire box
#             hx_swap_oob='true',
#             hx_ext='sse', 
#             sse_connect=f"/sse_output_monitor/o1_output?call_id={call_id}",
#             sse_event="o1_output_event",
#             sse_swap="message"
#             # sse_swap="innerHTML",
#             ).__html__(), 
#         Div(
#             P("Generating..."),
#             id='output-box4-content',
#             hx_swap='innerHTML', 
#             hx_swap_oob='true',
#             hx_ext='sse', 
#             sse_connect=f"/sse_output_monitor/challenger_output?call_id={call_id}",
#             sse_event="challenger_output_event",
#             # sse_swap="innerHTML",
#             sse_swap="message"
#         ).__html__(),
#     ])
#     return HTMLResponse(content=content + clear_submission_input().__html__())


@rt('/output', methods=['POST'])
async def output(user_input: str, session):
    '''
    This is the first call to get the candidate prompts.
    Candidate prompts are generated in a different thread, in the 
    meantime we display a loading message.
    '''
    call_id = str(uuid.uuid4())
    # Initialize 'outputs' in session if it doesn't exist, we'll listen for updates to this dict in the frontend
    if 'outputs' in session:
        del session['outputs']
    session.setdefault(f'outputs', {})
    generate_candidate_prompts(user_input, session, call_id)

    # o1_output, challenger_output = asyncio.run(run_generation_pipeline(user_input, session, call_id))
    # logger.debug(f"finished run_generation_pipeline for call_id: {call_id}, o1_output: {o1_output}, challenger_output: {challenger_output}")
    
    # asyncio.create_task(run_generation_pipeline(user_input, session, call_id))
    
    # TODO: move clearing the submission form to here?
    return display_generations(call_id)
    # return simple_generation_preview(call_id)

@rt('/process_additional_outputs', methods=['GET'])
def get(request):
# async def process_additional_outputs(o1_prompt_json, challenger_prompt_json, session, call_id):
    logger.debug(f"Processing additional outputs")
    # o1_prompt_json = session.get('o1_prompt_json', '')
    # challenger_prompt_json = session.get('challenger_prompt_json', '')
    # data = request.json()
    data = request.query_params
    box_id = data.get('box_id')
    prompt = data.get('prompt')
    call_id = data.get('call_id')

    # prompt = generations_tbl[f"{call_id}-{output_type}"]
    # prompt_json = prompt.output

    # Simulate processing delay
    import time
    time.sleep(0.1)  # Simulate delay

    logger.debug(f"Getting final outputs for: {user_input}")
    o1_prompt = call_dummy_llm(
        user_prompt=user_input,
        model_name="gpt-4o-mini",
        response_model=PromptModel,
        sleep_time=2
    )
    o1_prompt_json = o1_prompt.model_dump_json()
    o1_prompt_json = o1_prompt.user_prompt
    logger.debug(f"o1_prompt_json: {o1_prompt_json}")

    challenger_prompt = call_dummy_llm(
        system_prompt=PROMPT_GEN_SYSTEM_PROMPT,
        user_prompt=user_input,
        model_name="gpt-4o-mini",
        response_model=PromptModel
    )
    challenger_prompt_json = challenger_prompt.model_dump_json()
    challenger_prompt_json = challenger_prompt.user_prompt
    logger.debug(f"challenger_prompt_json: {challenger_prompt_json}")

    # insert the generation into the database
    session_id = session.get("session_id")

    logger.debug(f"Inserting generation into database: {call_id}-o1_prompt:\n{o1_prompt_json}")
    generations_tbl.insert(Generation(
        call_id=call_id + '-o1_prompt',
        session_id=session_id,
        call_type='o1_prompt',
        input=user_input, 
        output=o1_prompt_json, 
        timestamp=datetime.now().isoformat()
    ))

    logger.debug(f"Inserting generation into database: {call_id}-challenger_prompt:\n{challenger_prompt_json}")
    generations_tbl.insert(Generation(
        call_id=call_id + '-challenger_prompt',
        session_id=session_id,
        call_type='challenger_prompt',
        input=user_input, 
        output=challenger_prompt_json, 
        timestamp=datetime.now().isoformat()
    ))
    return o1_prompt_json, challenger_prompt_json

    # Process outputs based on `box_id`
    output_content = prompt.upper()

    # return output_content1, output_content2
    return Div(
        P(output_content),
        id=f'{box_id}-content',
    )

serve(
    reload=True,
    reload_excludes=['*.db', '*.db-journal'],
    host='0.0.0.0',
    port=5001
    )