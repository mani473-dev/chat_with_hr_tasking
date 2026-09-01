# ============================================================
# api.py
# ============================================================

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from state import TaskState
from task_router import task_router
from orchestrator import orchestrate
from conversation import handle_conversation


# ============================================================
# 1. FASTAPI APP
# ============================================================

app = FastAPI(
    title="HR Recruitment Tasking API"
)


# ============================================================
# 2. INTERNAL CONVERSATION ID
# ============================================================
#
# POC:
# The user does NOT need to send conversation_id.
#
# It is maintained internally.
#
# ============================================================

CONVERSATION_ID = "test123"


# ============================================================
# 3. IN-MEMORY CONVERSATION STORE
# ============================================================
#
# Stores pending state between requests.
#
# Example:
#
# {
#     "test123": {
#         "task_type": "SCHEDULE_INTERVIEW",
#         "candidate_name": "Jith Daniel",
#         "suggested_candidate": "Jithu Daniel",
#         ...
#     }
# }
#
# IMPORTANT:
# Restarting FastAPI clears this memory.
#
# ============================================================

CONVERSATIONS = {}


# ============================================================
# 4. REQUEST MODEL
# ============================================================

class UserRequest(BaseModel):

    question: str


# ============================================================
# 5. ROOT
# ============================================================

@app.get("/")
def home():

    return {
        "message":
            "HR Recruitment Tasking API is running"
    }


# ============================================================
# 6. EXECUTE
# ============================================================

@app.post("/execute")
def execute(
    request: UserRequest
):

    try:

        # ====================================================
        # STEP 1: GET USER QUESTION
        # ====================================================

        question = (
            request.question.strip()
        )

        if not question:

            raise HTTPException(
                status_code=400,
                detail="Question cannot be empty."
            )

        # ====================================================
        # STEP 2: INTERNAL CONVERSATION ID
        # ====================================================

        conversation_id = CONVERSATION_ID

        print(
            "\n========================================"
        )

        print(
            "USER QUESTION"
        )

        print(
            "========================================"
        )

        print(
            question
        )

        print(
            "\nCONVERSATION ID:"
        )

        print(
            conversation_id
        )

        # ====================================================
        # STEP 3: GET PREVIOUS STATE
        # ====================================================

        previous_state = (
            CONVERSATIONS.get(
                conversation_id
            )
        )

        print(
            "\n========================================"
        )

        print(
            "CONVERSATION MEMORY CHECK"
        )

        print(
            "========================================"
        )

        print(
            "Conversation ID:",
            conversation_id
        )

        print(
            "Stored conversations:",
            list(
                CONVERSATIONS.keys()
            )
        )

        print(
            "Previous state:"
        )

        print(
            previous_state
        )

        # ====================================================
        # STEP 4: HANDLE EXISTING CONVERSATION
        # ====================================================
        #
        # IMPORTANT:
        #
        # If a previous task is waiting for user input,
        # do NOT send the new message to task_router().
        #
        # Examples:
        #
        # "yes"
        # "no"
        # "Mamdouh Salem"
        # "Actually use Ahmed"
        # "44"
        # "change the time to 4 PM"
        #
        # All of these should be interpreted in the
        # context of the previous state.
        #
        # ====================================================

        if previous_state:

            waiting_for_user = (
                previous_state.get(
                    "waiting_for_user",
                    False
                )
            )

            awaiting_confirmation = (
                previous_state.get(
                    "awaiting_confirmation",
                    False
                )
            )

            if (
                waiting_for_user
                or
                awaiting_confirmation
            ):

                print(
                    "\n========================================"
                )

                print(
                    "CONTINUING EXISTING CONVERSATION"
                )

                print(
                    "========================================"
                )

                # ==================================================
                # SEND USER REPLY + PREVIOUS STATE TO CONVERSATION
                # ==================================================

                conversation_result = (
                    handle_conversation(
                        previous_state,
                        question
                    )
                )

                print(
                    "\n========================================"
                )

                print(
                    "CONVERSATION RESULT"
                )

                print(
                    "========================================"
                )

                print(
                    conversation_result
                )

                action = (
                    conversation_result.get(
                        "action"
                    )
                )

                # ==================================================
                # UPDATE CANDIDATE NAME
                # ==================================================

                candidate_name = (
                    conversation_result.get(
                        "candidate_name"
                    )
                )

                if candidate_name:

                    previous_state[
                        "candidate_name"
                    ] = candidate_name

                    previous_state[
                        "confirmed_candidate_name"
                    ] = candidate_name

                # ==================================================
                # UPDATE INTERVIEWER NAMES
                # ==================================================

                interviewer_names = (
                    conversation_result.get(
                        "interviewer_names"
                    )
                )

                if interviewer_names:

                    previous_state[
                        "interviewer_names"
                    ] = interviewer_names

                    previous_state[
                        "confirmed_interviewer_names"
                    ] = interviewer_names

                # ==================================================
                # UPDATE REQUISITION NUMBER
                # ==================================================

                requisition_number = (
                    conversation_result.get(
                        "requisition_number"
                    )
                )

                if requisition_number:

                    previous_state[
                        "requisition_number"
                    ] = requisition_number

                # ==================================================
                # UPDATE DATE
                # ==================================================

                date = (
                    conversation_result.get(
                        "date"
                    )
                )

                if date:

                    previous_state[
                        "date"
                    ] = date

                # ==================================================
                # UPDATE START DATETIME
                # ==================================================

                start_datetime = (
                    conversation_result.get(
                        "start_datetime"
                    )
                )

                if start_datetime:

                    previous_state[
                        "start_datetime"
                    ] = start_datetime

                # ==================================================
                # UPDATE END DATETIME
                # ==================================================

                end_datetime = (
                    conversation_result.get(
                        "end_datetime"
                    )
                )

                if end_datetime:

                    previous_state[
                        "end_datetime"
                    ] = end_datetime

                # ==================================================
                # ACTION: CANCEL
                # ==================================================

                if action == "CANCEL":

                    CONVERSATIONS.pop(
                        conversation_id,
                        None
                    )

                    message = (
                        conversation_result.get(
                            "message"
                        )
                        or
                        "The current task has been cancelled."
                    )

                    return {

                        "question":
                            question,

                        "task_type":
                            previous_state.get(
                                "task_type"
                            ),

                        "status":
                            "CANCELLED",

                        "state":
                            previous_state,

                        "message":
                            message
                    }

                # ==================================================
                # ACTION: WAIT
                # ==================================================
                #
                # The conversation is not complete.
                # Keep the state in memory.
                #
                # ==================================================

                if action == "WAIT":

                    previous_state[
                        "waiting_for_user"
                    ] = True

                    CONVERSATIONS[
                        conversation_id
                    ] = previous_state

                    message = (
                        conversation_result.get(
                            "message"
                        )
                        or
                        "Please provide the information needed to continue."
                    )

                    return {

                        "question":
                            question,

                        "task_type":
                            previous_state.get(
                                "task_type"
                            ),

                        "status":
                            "WAITING_FOR_USER",

                        "state":
                            previous_state,

                        "message":
                            message
                    }

                # ==================================================
                # ACTION:
                #
                # CONFIRM
                # CORRECT
                # UPDATE
                #
                # Continue the original task.
                # ==================================================

                if action in {
                    "CONFIRM",
                    "CORRECT",
                    "UPDATE"
                }:

                    previous_state[
                        "awaiting_confirmation"
                    ] = False

                    previous_state[
                        "confirmation_type"
                    ] = None

                    previous_state[
                        "waiting_for_user"
                    ] = False

                    # ------------------------------------------------
                    # Clear previous suggestions
                    # ------------------------------------------------

                    previous_state[
                        "suggested_candidate"
                    ] = None

                    previous_state[
                        "suggested_interviewer"
                    ] = None

                    # =================================================
                    # RESUME ORCHESTRATOR
                    # =================================================

                    print(
                        "\n========================================"
                    )

                    print(
                        "RESUMING PREVIOUS TASK"
                    )

                    print(
                        "========================================"
                    )

                    orchestration_result = (
                        orchestrate(
                            previous_state
                        )
                    )

                    previous_state.update(
                        orchestration_result
                    )

                    # =================================================
                    # SAVE OR CLEAR MEMORY
                    # =================================================

                    if (
                        previous_state.get(
                            "waiting_for_user",
                            False
                        )
                        or
                        previous_state.get(
                            "awaiting_confirmation",
                            False
                        )
                    ):

                        CONVERSATIONS[
                            conversation_id
                        ] = previous_state

                    else:

                        CONVERSATIONS.pop(
                            conversation_id,
                            None
                        )

                    # =================================================
                    # RETURN
                    # =================================================

                    return {

                        "question":
                            question,

                        "task_type":
                            previous_state.get(
                                "task_type"
                            ),

                        "route_reason":
                            previous_state.get(
                                "route_reason"
                            ),

                        "status":
                            (
                                "WAITING_FOR_USER"
                                if previous_state.get(
                                    "waiting_for_user",
                                    False
                                )
                                else
                                "COMPLETED"
                            ),

                        "state":
                            previous_state,

                        "message":
                            previous_state.get(
                                "final_response"
                            )
                    }

                # ==================================================
                # UNKNOWN ACTION
                # ==================================================

                previous_state[
                    "waiting_for_user"
                ] = True

                CONVERSATIONS[
                    conversation_id
                ] = previous_state

                return {

                    "question":
                        question,

                    "task_type":
                        previous_state.get(
                            "task_type"
                        ),

                    "status":
                        "WAITING_FOR_USER",

                    "state":
                        previous_state,

                    "message":
                        (
                            conversation_result.get(
                                "message"
                            )
                            or
                            "Please provide the information needed to continue."
                        )
                }

        # ====================================================
        # STEP 5: CREATE NEW STATE
        # ====================================================

        state: TaskState = {

            "question":
                question,

            "waiting_for_user":
                False,

            "awaiting_confirmation":
                False
        }

        # ====================================================
        # STEP 6: TASK ROUTER
        # ====================================================

        print(
            "\n========================================"
        )

        print(
            "CALLING TASK ROUTER"
        )

        print(
            "========================================"
        )

        router_result = (
            task_router(
                state
            )
        )

        # ====================================================
        # MERGE ROUTER RESULT
        # ====================================================

        state.update(
            router_result
        )

        print(
            "\nTASK TYPE:"
        )

        print(
            state.get(
                "task_type"
            )
        )

        # ====================================================
        # STEP 7: ORCHESTRATOR
        # ====================================================

        print(
            "\n========================================"
        )

        print(
            "CALLING ORCHESTRATOR"
        )

        print(
            "========================================"
        )

        orchestration_result = (
            orchestrate(
                state
            )
        )

        # ====================================================
        # MERGE ORCHESTRATION RESULT
        # ====================================================

        state.update(
            orchestration_result
        )

        # ====================================================
        # STEP 8: SAVE CONVERSATION WHEN REQUIRED
        # ====================================================

        waiting_for_user = (
            state.get(
                "waiting_for_user",
                False
            )
        )

        awaiting_confirmation = (
            state.get(
                "awaiting_confirmation",
                False
            )
        )

        if (
            waiting_for_user
            or
            awaiting_confirmation
        ):

            print(
                "\n========================================"
            )

            print(
                "SAVING CONVERSATION STATE"
            )

            print(
                "========================================"
            )

            CONVERSATIONS[
                conversation_id
            ] = state

            print(
                "Conversation ID:",
                conversation_id
            )

            print(
                "waiting_for_user:",
                waiting_for_user
            )

            print(
                "awaiting_confirmation:",
                awaiting_confirmation
            )

            print(
                "confirmation_type:",
                state.get(
                    "confirmation_type"
                )
            )

            print(
                "suggested_candidate:",
                state.get(
                    "suggested_candidate"
                )
            )

            print(
                "suggested_interviewer:",
                state.get(
                    "suggested_interviewer"
                )
            )

        else:

            CONVERSATIONS.pop(
                conversation_id,
                None
            )

        # ====================================================
        # STEP 9: RETURN RESPONSE
        # ====================================================

        return {

            "question":
                question,

            "task_type":
                state.get(
                    "task_type"
                ),

            "route_reason":
                state.get(
                    "route_reason"
                ),

            "status":
                (
                    "WAITING_FOR_USER"
                    if state.get(
                        "waiting_for_user",
                        False
                    )
                    else
                    "COMPLETED"
                ),

            "state":
                state,

            "message":
                state.get(
                    "final_response"
                )
        }

    # ========================================================
    # HTTP EXCEPTION
    # ========================================================

    except HTTPException:

        raise

    # ========================================================
    # GENERAL EXCEPTION
    # ========================================================

    except Exception as e:

        print(
            "\n========================================"
        )

        print(
            "ERROR"
        )

        print(
            "========================================"
        )

        print(
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )