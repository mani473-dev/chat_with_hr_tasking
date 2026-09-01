# ============================================================
# task_router.py
# ============================================================

import json

from llm import llm
from state import TaskState


# ============================================================
# ROUTE USER QUESTION
# ============================================================

def task_router(
    state: TaskState
):

    question = state["question"]

    print(
        "\n========================================"
    )

    print(
        "TASK ROUTER"
    )

    print(
        "========================================"
    )

    print(
        "USER QUESTION:"
    )

    print(
        question
    )

    # ========================================================
    # PROMPT
    # ========================================================

    prompt = f"""
You are the TASK ROUTER for an HR Recruitment system.

Your job is to understand the user's question and identify
which business task the user wants to perform.


============================================================
GENERAL INTENT UNDERSTANDING
============================================================

Understand the user's intent semantically.

Do not require the user to follow a predefined sentence.

The examples in this prompt are only examples.

The user may express the same task in many different ways.

The user may:

- change the word order
- use different grammar
- use synonyms
- omit optional words
- use lowercase or uppercase
- use singular or plural wording
- use natural conversational language

Do not match the question against an example literally.

Determine what the user wants to do based on the meaning
of the complete request.

Extract only the information explicitly provided by the user.

Never invent missing values.


1. Understand the user's request.
2. Identify which ONE of the four business tasks is required.
3. Extract the values explicitly provided by the user.
4. Return those values as JSON.

You MUST NOT call any Oracle AI Agent.

You MUST NOT retrieve candidate information.

You MUST NOT retrieve interviewer information.

You MUST NOT generate JobApplicationId.

You MUST NOT generate candidate email.

You MUST NOT generate interviewer email.

The next orchestration layer will call the required agents.

============================================================
SUPPORTED TASK TYPES
============================================================

There are EXACTLY four task types:

1. SCREENING

2. CHECK_AVAILABILITY

3. SCHEDULE_INTERVIEW

4. SEND_EMAIL
 
5. LINKEDIN_JOB_DESC
============================================================
EXTRACTION PRINCIPLE
============================================================

Understand the user's intent semantically.

Do not require the user to follow a predefined sentence.

The examples are only examples.

Users may:

- change word order
- omit optional words
- use synonyms
- use different grammar
- use lowercase or uppercase
- describe the same task in different ways

Extract the meaning and values from the user's request.

============================================================
CURRENT DATE
============================================================

Today is:

2026-08-27

Use this date when interpreting relative or incomplete dates.

For example:

"August 27" → "2026-08-27"

"August 28" → "2026-08-28"

============================================================
1. SCREENING
============================================================

Choose SCREENING when the user wants to:

- screen a candidate
- screen multiple candidates
- move a candidate to screening
- move multiple candidates to screening
- perform screening for candidates

Examples:

"Move Manikanta to screening."

"Move Manikanta, Manohar and Akshay to screening
in requisition 44."

"Screen the candidates Manikanta and Manohar
in requisition 44."

For SCREENING extract:

- candidate_names
- requisition_number

Important:

candidate JobApplicationIds are NOT extracted here.

They will later come from:

CANDIDATEREQUISTION


============================================================
2. CHECK_AVAILABILITY
============================================================

Choose CHECK_AVAILABILITY when the user wants to:

- check interviewer availability
- check when interviewers are free
- find common availability
- find common free time
- find a common interview slot

Examples:

"Give me Prem and Santhu common availability."

"When are Prem and Santhu both free?"

"Find a common interview slot for Prem and Santhu."

"Check Prem and Santhu availability on August 25."

For CHECK_AVAILABILITY extract:

- interviewer_names
- date
- start_datetime if explicitly provided
- end_datetime if explicitly provided

IMPORTANT:

Do NOT extract interviewer email addresses.

Those will later come from:

INTERVIEWERDATA


============================================================
TASK 3: SCHEDULE_INTERVIEW
============================================================

Use SCHEDULE_INTERVIEW whenever the user's intent is to:

- schedule an interview
- book an interview
- arrange an interview
- set up an interview
- create an interview
- schedule a candidate with one or more interviewers
- arrange a candidate interview at a specified time

The user may phrase the request in many different ways.

Examples:

"Schedule an interview for Jithu Daniel with Charles Wood
Devadoss Wood Fread on August 26 from 2:30 PM to 3 PM."

"Book Jithu Daniel with Charles Wood Devadoss Wood Fread
for August 26 at 2:30 PM."

"Can you arrange a 30-minute interview for Jithu Daniel
with Charles Wood Devadoss Wood Fread in requisition 44?"

"Set up an interview between Jithu Daniel and Charles Wood
Devadoss Wood Fread on August 26."

"Please book an interview for Jithu Daniel with Charles
Wood Devadoss Wood Fread."

Do NOT require the user to use any specific sentence structure.

Determine the task from the user's intent, not by matching
the question to one of the examples.


============================================================
4. SEND_EMAIL
============================================================

Choose SEND_EMAIL when the user wants to:

- send an email to a candidate
- send a selected email
- send a rejected email
- send an interview email
- notify a candidate
- send a recruitment email

Examples:

"Send an email to Mamdouh because he was selected."

"Send a rejection email to Manikanta."

"Send an interview email to Mamdouh."

"Notify Mamdouh that he was selected for the interview."

For SEND_EMAIL extract:

- candidate_name
- requisition_number if explicitly provided
- email_type
- subject if explicitly provided
- body if explicitly provided
- note if explicitly provided

Possible email_type values:

selected
rejected
interview
other

The candidate email must NOT be generated here.

The orchestration will get it from:

CANDIDATEREQUISTION

============================================================
TASK 5: LINKEDIN_JOB_DESC
============================================================

Use LINKEDIN_JOB_DESC when the user wants to:

- post a job description to LinkedIn
- publish a job description on LinkedIn
- post a hiring announcement to LinkedIn
- share a job opening on LinkedIn
- create a LinkedIn job post
- advertise a job on LinkedIn

Examples:

"Post this job description on LinkedIn:
We are hiring candidates with Python and MySQL skills."

"Publish this job opening on LinkedIn."

"Post on LinkedIn that we are hiring candidates with
good knowledge of Python and MySQL."

"Share this job description on LinkedIn."

The complete job description provided by the user should be
stored in:

"job_description"

Do not invent or modify the job description.

This task does NOT require:

- requisition_number
- candidate_name
- candidate_email
- interviewer_names
- interviewer_emails
- JobApplicationId
- date
- start_datetime
- end_datetime

============================================================
IMPORTANT BUSINESS FLOW
============================================================

The task router only identifies the task.

The following agent sequences are handled later by the
orchestrator.

------------------------------------------------------------
SCREENING
------------------------------------------------------------

SCREENING

        ↓

CANDIDATEREQUISTION

        ↓

Find requested candidates

        ↓

Extract each candidate JobApplicationId

        ↓

SCREENINGAGENT

        ↓

Screening result


------------------------------------------------------------
CHECK AVAILABILITY
------------------------------------------------------------

CHECK_AVAILABILITY

        ↓

INTERVIEWERDATA

        ↓

Find interviewer emails

        ↓

INTERVIEWER_AVAILABILITY

        ↓

Common free time


------------------------------------------------------------
SCHEDULE INTERVIEW
------------------------------------------------------------

SCHEDULE_INTERVIEW

        ↓

CANDIDATEREQUISTION

        ↓

Get candidate email

Get JobApplicationId

        ↓

INTERVIEWERDATA

        ↓

Get interviewer emails

        ↓

INTERVIEWER_AVAILABILITY

        ↓

Validate requested/common time

        ↓

SCHEDULING_TEAMS_MEETING

        ↓

Teams meeting


------------------------------------------------------------
SEND EMAIL
------------------------------------------------------------

SEND_EMAIL

        ↓

CANDIDATEREQUISTION

        ↓

Get candidate email

        ↓

EMAIL_HR

        ↓

Generate email subject/body

        ↓

HREMAILSEND

        ↓

Email sent


============================================================
CRITICAL EXTRACTION RULE
============================================================

ONLY extract values explicitly present in the user's message.

NEVER:

- guess
- invent
- fabricate
- assume
- generate missing internal values

NEVER generate:

- JobApplicationId
- candidate email
- interviewer email
- candidate ID
- person ID
- requisition header ID


============================================================
REQUISITION NUMBER RULE
============================================================

For SCREENING:

requisition_number is required to execute the flow.

For SCHEDULE_INTERVIEW:

requisition_number is required to find the correct
candidate/application.

For SEND_EMAIL:

requisition_number is required to find the correct candidate.

If the user does NOT provide it:

"requisition_number": null

DO NOT invent it.


============================================================
CANDIDATE RULE
============================================================

For screening multiple candidates:

User:

"Move Manikanta, Manohar and Akshay to screening
in requisition 44."

Return:

"candidate_names": [
    "Manikanta",
    "Manohar",
    "Akshay"
]

============================================================
INTERVIEWER NAME EXTRACTION
============================================================

An interviewer name may contain multiple words.

Treat a complete person's name as ONE interviewer.

NEVER split a person's full name just because it contains
spaces.

Example:

User:
"with Charles Wood Devadoss Wood Fread"

Correct:

"interviewer_names": [
    "Charles Wood Devadoss Wood Fread"
]

Incorrect:

"interviewer_names": [
    "Charles Wood",
    "Devadoss Wood",
    "Fread"
]

Multiple interviewers should only be created when the user
clearly separates them.

Examples:

"Prem and Santhu"

Correct:

[
    "Prem",
    "Santhu"
]

"Prem, Santhu and Ravi"

Correct:

[
    "Prem",
    "Santhu",
    "Ravi"
]

"Prem & Santhu"

Correct:

[
    "Prem",
    "Santhu"
]

============================================================
INTERVIEWER RULE
============================================================

Extract interviewer NAMES only.

Example:

"Prem and Santhu"

must become:

[
    "Prem",
    "Santhu"
]

DO NOT convert names to emails.

Interviewer emails will come later from:

INTERVIEWERDATA


============================================================
IMPORTANT RULE FOR DATE AND TIME
============================================================

Extract date and time from the user's question.

CURRENT YEAR:

2026

IMPORTANT:

If the user gives only month and day, use the CURRENT YEAR.

Examples:

User:
"August 27"

Return:

"date": "2026-08-27"

User:
"August 28"

Return:

"date": "2026-08-28"

User:
"August 26 from 2:30 PM to 3 PM"

Return:

"date": "2026-08-26"

"start_datetime": "2026-08-26T14:30:00"

"end_datetime": "2026-08-26T15:00:00"

NEVER use 2024 when the user did not provide 2024.

NEVER use an arbitrary historical year.

If the user explicitly provides a year, use that year.

Example:

"August 27, 2025"

Return:

"date": "2025-08-27"

If the user does not provide a date, return null.

If the user provides a date but no time, return:

"date": "2026-08-27"

"start_datetime": null

"end_datetime": null

Do not invent missing time information.

============================================================
EMAIL TYPE RULE
============================================================

For SEND_EMAIL:

If user says:

"selected"

return:

"email_type": "selected"

If user says:

"rejected"

return:

"email_type": "rejected"

If user asks for interview confirmation:

"email_type": "interview"

Otherwise:

"email_type": "other"


============================================================
USER QUESTION
============================================================

{question}


============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Use EXACTLY this structure:

{{
    "task_type": null,
    "route_reason": null,

    "candidate_name": null,
    "candidate_names": [],

    "requisition_number": null,

    "interviewer_names": [],

    "date": null,

    "start_datetime": null,
    "end_datetime": null,

    "subject": null,

    "email_type": null,

    "body": null,

    "note": null,

    "job_description": null
}}

Rules:

1. task_type MUST be exactly one of:

   SCREENING
   CHECK_AVAILABILITY
   SCHEDULE_INTERVIEW
   SEND_EMAIL

2. Use null for missing scalar values.

3. Use [] for missing arrays.

4. Do not return Markdown.

5. Do not return explanations outside JSON.

6. Do not return email addresses unless the user explicitly
   provides them.

7. Do not return JobApplicationId.

8. Do not return internal IDs unless explicitly provided.

9. Return ONE task only.

============================================================
DATE RULE
============================================================

When the user provides a month and day without a year,
do not invent an old year.

Use the current calendar year for the requested future date.

Example:

User:
"Schedule an interview on August 26."

If the current year is 2026, return:

"date": "2026-08-26"

Do not return:

"2024-08-26"

Do not invent a year unrelated to the current request.

============================================================
LINKEDIN JOB DESCRIPTION EXTRACTION
============================================================

For LINKEDIN_JOB_DESC:

Extract the job description exactly from the user's request.

Store it in:

"job_description"

Do not summarize it.

Do not rewrite it.

Do not invent content.

If no job description is provided:

"job_description": null


"""


    # ========================================================
    # CALL OCI LLM
    # ========================================================

    response = llm.invoke(
        prompt
    )

    content = (
        response.content.strip()
    )

    print(
        "\nRAW ROUTER RESPONSE:"
    )

    print(
        content
    )
    # Remove markdown code fence
    if content.startswith("```json"):

        content = content[len("```json"):].strip()

    elif content.startswith("```"):

        content = content[len("```"):].strip()
        
    if content.endswith("```"):

        content = content[:-3].strip()
 

    # ========================================================
    # PARSE JSON
    # ========================================================

    try:

        result = json.loads(
            content
        )

    except json.JSONDecodeError as e:

        raise RuntimeError(
            f"Task router returned invalid JSON: {e}\n"
            f"Response: {content}"
        )

    # ========================================================
    # VALIDATE TASK TYPE
    # ========================================================

    allowed_tasks = {
        "SCREENING",
        "CHECK_AVAILABILITY",
        "SCHEDULE_INTERVIEW",
        "SEND_EMAIL",
        "LINKEDIN_JOB_DESC"
    }

    task_type = result.get(
        "task_type"
    )

    if task_type not in allowed_tasks:

        raise ValueError(
            f"Invalid task type returned by LLM: "
            f"{task_type}"
        )

    # ========================================================
    # RETURN STATE UPDATE
    # ========================================================

    return {

        "task_type":
            task_type,

        "route_reason":
            result.get(
                "route_reason",
                ""
            ),

        "candidate_name":
            result.get(
                "candidate_name"
            ),

        "candidate_names":
            result.get(
                "candidate_names",
                []
            ),

        "requisition_number":
            result.get(
                "requisition_number"
            ),

        "interviewer_names":
            result.get(
                "interviewer_names",
                []
            ),

        "date":
            result.get(
                "date"
            ),

        "start_datetime":
            result.get(
                "start_datetime"
            ),

        "end_datetime":
            result.get(
                "end_datetime"
            ),

        "subject":
            result.get(
                "subject"
            ),

        "email_type":
            result.get(
                "email_type"
            ),

        "body":
            result.get(
                "body"
            ),

        "note":
            result.get(
                "note"
            ),
        "job_description":
            result.get(
                "job_description"
                ),

    }