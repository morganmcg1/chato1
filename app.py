from fasthtml.common import *

from prompt_models import (
    PROMPT_GEN_SYSTEM_PROMPT,
    PROMPT_GEN_PROMPT,
    PromptModel,
    call_llm,
    call_dummy_llm
)

import html
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app, rt = fast_app(
    pico=False, # Disable Pico.css to prevent style conflicts
    hdrs=(
        Link(rel='stylesheet', href='https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap'),
        Script(src="https://unpkg.com/htmx.org@1.9.2"),
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

@rt('/')
def get():
    return Titled(
        "Prompt Battle",
        style,
        H2("Welcome to Prompt Battle"),
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
        ),
        Div(
            create_submission_form(),
            style='position: fixed; bottom: 20px; left: 0; right: 0; background: #fff; padding: 10px 20px;'
        )
    )

def create_submission_form():
    return Form(
        Div(
            Input(type='text', name='user_input', placeholder='Enter something'),
            Button('Submit', type='submit', cls='submit-button'),
            cls='input-form'
        ),
        method='post',
        hx_post='/output',                   # htmx attribute to make an AJAX POST request
        hx_swap='none',                 # Swap strategy (replace inner HTML)
        style='margin: 0;'
    )

def create_output_box(box_id):
    return Div(
        Div(id=f'{box_id}-content', cls='output-content'),
        id=box_id,
        cls='output-box',
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
            hx_trigger='outputs1and2Loaded from:window',
            hx_get=f'/process_additional_outputs?box_id={box_id}',
            hx_swap='innerHTML',
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


@rt('/output', methods=['POST'])
def output(user_input: str, session):

    o1_prompt = call_dummy_llm(
        user_prompt=user_input,
        model_name="gpt-4o-mini",
        response_model=PromptModel
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

    session['o1_prompt_json'] = o1_prompt_json
    session['challenger_prompt_json'] = challenger_prompt_json
    
    # Build the content to return as a list of Divs so that both outputs can be returned
    content = ''.join([
        Div(
            P(o1_prompt_json),
            id='output-box1-content',
            hx_swap_oob='true',
        ).__html__(),  # Convert to HTML string
        Div(
            P(challenger_prompt_json),
            id='output-box2-content',
            hx_swap_oob='true',
        ).__html__(),
    ])

    # Create the response with the HX-Trigger header
    response = HTMLResponse(content=content)
    response.headers['HX-Trigger'] = 'outputs1and2Loaded'
    logger.debug(f"response: {response}")
    return response


@rt('/process_additional_outputs', methods=['GET'])
def process_additional_outputs(box_id: str, session):
    o1_prompt_json = session.get('o1_prompt_json', '')
    challenger_prompt_json = session.get('challenger_prompt_json', '')

    # Simulate processing delay
    import time
    time.sleep(0.5)  # Simulate delay

    # Process outputs based on `box_id`
    if box_id == 'output-box3':
        output_content = o1_prompt_json.upper()
    elif box_id == 'output-box4':
        output_content = challenger_prompt_json.upper()
    else:
        err_msg = f'Invalid box ID: `{box_id}`, - cannot pass content on to correct output box'
        output_content = err_msg
        logger.error(err_msg)
        

    return Div(
        P(output_content),
        id=f'{box_id}-content',
    )

serve()