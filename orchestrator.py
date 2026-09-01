# ============================================================
# orchestrator.py
# ============================================================

import json
from datetime import datetime

from agents import AGENTS
from oci_test import call_agent
from state import TaskState
from candidate_resolver import (
    resolve_candidate,
    name_similarity
)


# ============================================================
# GENERAL HELPER
# ============================================================

def print_agent_result(
    agent_name: str,
    result: dict
):
    print("\n========================================")
    print(f"{agent_name} RESULT")
    print("========================================")
    print(json.dumps(result, indent=4, default=str))


# ============================================================
# BUILD BODY FROM agents.py
# ============================================================

def build_agent_body(
    agent_name: str,
    parameters: dict
):
    agent_config = AGENTS.get(agent_name)

    if agent_config is None:
        raise ValueError(
            f"Agent not found in agents.py: {agent_name}"
        )

    body_template = (
        agent_config["body"]["parameters"]
    )

    body = {"parameters": {}}

    for parameter_name, template_value in body_template.items():
        if parameter_name == "triggerType":
            body["parameters"][parameter_name] = "REST"
            continue

        if parameter_name in parameters:
            dynamic_value = parameters.get(parameter_name)
            if dynamic_value is not None:
                body["parameters"][parameter_name] = dynamic_value
                continue

        body["parameters"][parameter_name] = template_value

    return body
# ============================================================
# VALIDATE INTERVIEW DATE/TIME
# ============================================================

def validate_interview_datetime(
    start_datetime: str,
    end_datetime: str
):

    if not start_datetime or not end_datetime:

        return {
            "valid": False,
            "message":
                "Interview start and end time are required."
        }

    try:

        start_dt = datetime.fromisoformat(
            start_datetime
        )

        end_dt = datetime.fromisoformat(
            end_datetime
        )

    except ValueError:

        return {
            "valid": False,
            "message":
                "The interview date/time format is invalid."
        }

    # ========================================================
    # START MUST BE BEFORE END
    # ========================================================

    if start_dt >= end_dt:

        return {
            "valid": False,
            "message":
                "The interview start time must be before the end time."
        }

    # ========================================================
    # CURRENT DATE/TIME
    # ========================================================

    if start_dt.tzinfo:

        now = datetime.now(
            tz=start_dt.tzinfo
        )

    else:

        now = datetime.now()

    # ========================================================
    # CHECK PAST DATE/TIME
    # ========================================================

    if start_dt < now:

        return {
            "valid": False,
            "message":
                (
                    f"The requested interview time "
                    f"{start_datetime} to {end_datetime} "
                    f"has already passed. "
                    f"Please provide a future date and time."
                )
        }

    return {
        "valid": True
    }

# ============================================================
# SCREENING FLOW
# ============================================================

def screening_flow(
    state: TaskState
):
    print("\n========================================")
    print("START SCREENING FLOW")
    print("========================================")

    requisition_number = state.get("requisition_number")
    candidate_names = state.get("candidate_names", [])

    if not requisition_number:
        return {
            "waiting_for_user": True,
            "missing_information": ["requisition_number"],
            "final_response": (
                "Which requisition number are these candidates associated with?"
            )
        }

    if not candidate_names:
        return {
            "waiting_for_user": True,
            "missing_information": ["candidate_names"],
            "final_response": "Please provide the candidate name(s) to screen."
        }

    candidate_parameters = {
        "RequisitionNumber": requisition_number
    }

    candidate_body = build_agent_body(
        "CANDIDATEREQUISTION",
        candidate_parameters
    )

    print("\nCalling CANDIDATEREQUISTION...")

    candidate_result = call_agent(
        "CANDIDATEREQUISTION",
        candidate_body
    )

    print_agent_result(
        "CANDIDATEREQUISTION",
        candidate_result
    )

    # ========================================================
    # RESOLVE EVERY CANDIDATE USING SHARED RESOLVER
    # ========================================================

    job_application_ids = []
    matched_candidates = []

    for requested_name in candidate_names:
        candidate_match = resolve_candidate(
            candidate_result,
            requested_name
        )

        if not candidate_match:
            return {
                "candidate_result": candidate_result,
                "candidate_name": requested_name,
                "waiting_for_user": False,
                "final_response": (
                    f"I could not find a candidate matching "
                    f"'{requested_name}' in requisition {requisition_number}."
                )
            }

        if candidate_match["status"] == "SUGGEST":
            suggested_name = candidate_match["candidate_name"]

            return {
                "candidate_result": candidate_result,
                "waiting_for_user": True,
                "awaiting_confirmation": True,
                "confirmation_type": "candidate",
                "original_candidate_input": requested_name,
                "suggested_candidate": suggested_name,
                "candidate_names": candidate_names,
                "requisition_number": requisition_number,
                "final_response": (
                    f"I couldn't find an exact match for '{requested_name}'. "
                    f"Did you mean '{suggested_name}'?"
                )
            }

        candidate = candidate_match["candidate"]
        job_application_id = candidate_match["jobApplicationId"]

        if not job_application_id:
            return {
                "candidate_result": candidate_result,
                "waiting_for_user": False,
                "final_response": (
                    f"JobApplicationId was not found for "
                    f"{candidate_match['candidate_name']}."
                )
            }

        job_application_ids.append(str(job_application_id))
        matched_candidates.append(candidate)

        print("\nCandidate matched:")
        print(candidate_match["candidate_name"])
        print("JobApplicationId:", job_application_id)

    # ========================================================
    # SCREENING AGENT
    # ========================================================

    screening_parameters = {
        "JobApplicationId": job_application_ids
    }

    screening_body = build_agent_body(
        "SCREENINGAGENT",
        screening_parameters
    )

    print("\nCalling SCREENINGAGENT...")

    screening_result = call_agent(
        "SCREENINGAGENT",
        screening_body
    )

    print_agent_result(
        "SCREENINGAGENT",
        screening_result
    )

    return {
        "candidate_result": candidate_result,
        "candidate_names": [
            candidate.get("CandidateName")
            for candidate in matched_candidates
        ],
        "job_application_ids": job_application_ids,
        "screening_result": screening_result,
        "waiting_for_user": False,
        "final_response": "Candidate screening completed successfully."
    }


# ============================================================
# AVAILABILITY FLOW
# ============================================================

def availability_flow(
    state: TaskState
):
    print("\n========================================")
    print("START AVAILABILITY FLOW")
    print("========================================")

    interviewer_names = state.get("interviewer_names", [])
    requisition_number = state.get("requisition_number")
    date = state.get("date")

    if isinstance(interviewer_names, str):
        interviewer_names = [interviewer_names]

    interviewer_names = [
        str(name).strip()
        for name in interviewer_names
        if str(name).strip()
    ]

    missing = []

    if not interviewer_names:
        missing.append("interviewer_names")

    if not requisition_number:
        missing.append("requisition_number")

    if not date:
        missing.append("date")

    if missing:
        return {
            "waiting_for_user": True,
            "missing_information": missing,
            "final_response": "Please provide the missing interviewer, requisition number, and date information."
        }

    interviewer_parameters = {
        "RequisitionNumber": requisition_number
    }

    interviewer_body = build_agent_body(
        "INTERVIEWERDATA",
        interviewer_parameters
    )

    print("\nCalling INTERVIEWERDATA...")

    interviewer_result = call_agent(
        "INTERVIEWERDATA",
        interviewer_body
    )

    print_agent_result(
        "INTERVIEWERDATA",
        interviewer_result
    )

    interviewer_match = resolve_interviewers(
        interviewer_result,
        interviewer_names
    )

    if interviewer_match["status"] == "NOT_FOUND":
        return {
            "interviewer_result": interviewer_result,
            "requested_interviewers": interviewer_names,
            "waiting_for_user": True,
            "awaiting_confirmation": True,
            "confirmation_type": "interviewer",
            "original_interviewer_input": interviewer_names,
            "final_response": (
                "I could not find the requested interviewer(s)."
            )
        }

    matches = interviewer_match["matches"]

    canonical_names = [
        item["actual_name"]
        for item in matches
    ]

    interviewer_emails = [
        item["email"]
        for item in matches
        if item.get("email")
    ]

    if not interviewer_emails:
        return {
            "interviewer_result": interviewer_result,
            "requested_interviewers": interviewer_names,
            "interviewer_emails": [],
            "waiting_for_user": False,
            "final_response": "No email addresses were found for the requested interviewer(s)."
        }

    if len(interviewer_emails) != len(canonical_names):
        return {
            "interviewer_result": interviewer_result,
            "requested_interviewers": interviewer_names,
            "interviewer_emails": interviewer_emails,
            "waiting_for_user": False,
            "final_response": "I could not find email addresses for all requested interviewers."
        }

    availability_parameters = {
        "interviewer_emails": interviewer_emails,
        "date": date,
        "meeting_duration_minutes": 30
    }

    availability_body = build_agent_body(
        "INTERVIEWER_AVAILABILITY",
        availability_parameters
    )

    print("\nCalling INTERVIEWER_AVAILABILITY...")
    print(json.dumps(availability_body, indent=4, default=str))

    try:
        availability_result = call_agent(
            "INTERVIEWER_AVAILABILITY",
            availability_body
        )
    except Exception as e:
        return {
            "interviewer_result": interviewer_result,
            "interviewer_emails": interviewer_emails,
            "availability_result": None,
            "waiting_for_user": False,
            "final_response": f"Interviewer availability check failed: {str(e)}"
        }

    print_agent_result(
        "INTERVIEWER_AVAILABILITY",
        availability_result
    )

    common_slots = extract_common_slots(
        availability_result
    )

    if not common_slots:
        return {
            "interviewer_result": interviewer_result,
            "requested_interviewers": canonical_names,
            "interviewer_emails": interviewer_emails,
            "availability_result": availability_result,
            "common_slots": [],
            "waiting_for_user": False,
            "final_response": (
                "No common free time was found for the requested "
                f"interviewer(s) on {date}."
            )
        }

    return {
        "interviewer_result": interviewer_result,
        "requested_interviewers": canonical_names,
        "interviewer_emails": interviewer_emails,
        "availability_result": availability_result,
        "common_slots": common_slots,
        "waiting_for_user": False,
        "final_response": "Interviewer availability check completed successfully."
    }


# ============================================================
# MATCH INTERVIEWERS
# ============================================================

def resolve_interviewers(
    interviewer_result,
    requested_names
):
    output = interviewer_result.get("output")

    if output is None:
        return {"status": "NOT_FOUND", "matches": []}

    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            return {"status": "NOT_FOUND", "matches": []}

    interviewer_list = output.get("result", [])

    if not isinstance(interviewer_list, list):
        return {"status": "NOT_FOUND", "matches": []}

    requested_names = [
        str(name).strip()
        for name in requested_names
        if str(name).strip()
    ]

    matches = []

    for requested_name in requested_names:
        best_match = None
        best_score = 0.0

        for interviewer in interviewer_list:
            display_name = interviewer.get("DisplayName")

            if not display_name:
                continue

            score = name_similarity(
                requested_name,
                display_name
            )

            if score > best_score:
                best_score = score
                best_match = interviewer

        if best_match and best_score >= 0.75:
            matches.append({
                "requested_name": requested_name,
                "actual_name": best_match.get("DisplayName"),
                "email": best_match.get("WorkEmail"),
                "score": best_score
            })

    # Handle one full interviewer name accidentally split by the router.
    if not matches and len(requested_names) > 1:
        combined_name = " ".join(requested_names)

        best_match = None
        best_score = 0.0

        for interviewer in interviewer_list:
            display_name = interviewer.get("DisplayName")

            if not display_name:
                continue

            score = name_similarity(
                combined_name,
                display_name
            )

            if score > best_score:
                best_score = score
                best_match = interviewer

        if best_match and best_score >= 0.75:
            matches = [{
                "requested_name": combined_name,
                "actual_name": best_match.get("DisplayName"),
                "email": best_match.get("WorkEmail"),
                "score": best_score
            }]

    if not matches:
        return {"status": "NOT_FOUND", "matches": []}

    return {
        "status": "FOUND",
        "matches": matches
    }


# ============================================================
# SCHEDULING FLOW
# ============================================================

def scheduling_flow(
    state: TaskState
):
    print("\n========================================")
    print("START SCHEDULING FLOW")
    print("========================================")

    candidate_name = state.get("candidate_name")
    requisition_number = state.get("requisition_number")
    interviewer_names = state.get("interviewer_names", [])
    start_datetime = state.get("start_datetime")
    end_datetime = state.get("end_datetime")
    subject = state.get("subject") or "Java Interview"

    if not candidate_name:
        return {"final_response": "Candidate name is required."}

    if not requisition_number:
        return {
            "waiting_for_user": True,
            "missing_information": ["requisition_number"],
            "final_response": (
                f"Which requisition number is {candidate_name} associated with?"
            )
        }

    if not interviewer_names:
        return {"final_response": "Interviewer name is required."}

    if not start_datetime or not end_datetime:
        return {"final_response": "Please provide the interview date and time."}
    # ========================================================
# 2A. VALIDATE INTERVIEW DATE/TIME
# ========================================================

    datetime_validation = (
    validate_interview_datetime(
        start_datetime,
        end_datetime
    )
)

    if not datetime_validation["valid"]:

        return {

        "waiting_for_user":
            True,

        "missing_information":
            [
                "future_interview_datetime"
            ],

        "final_response":
            datetime_validation["message"]
    }

    # ========================================================
    # CANDIDATEREQUISTION
    # ========================================================

    candidate_body = build_agent_body(
        "CANDIDATEREQUISTION",
        {"RequisitionNumber": requisition_number}
    )

    print("\nCalling CANDIDATEREQUISTION...")

    candidate_result = call_agent(
        "CANDIDATEREQUISTION",
        candidate_body
    )

    print_agent_result(
        "CANDIDATEREQUISTION",
        candidate_result
    )

    # ========================================================
    # RESOLVE CANDIDATE USING SHARED RESOLVER
    # ========================================================

    candidate_match = resolve_candidate(
        candidate_result,
        candidate_name
    )

    if not candidate_match:
        return {
            "candidate_result": candidate_result,
            "waiting_for_user": False,
            "final_response": (
                f"I could not find a candidate matching '{candidate_name}' "
                f"in requisition {requisition_number}."
            )
        }

    if candidate_match["status"] == "SUGGEST":
        suggested_name = candidate_match["candidate_name"]

        return {
            "candidate_result": candidate_result,
            "waiting_for_user": True,
            "awaiting_confirmation": True,
            "confirmation_type": "candidate",
            "original_candidate_input": candidate_name,
            "suggested_candidate": suggested_name,
            "requisition_number": requisition_number,
            "interviewer_names": interviewer_names,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "subject": subject,
            "final_response": (
                f"I couldn't find an exact match for '{candidate_name}'. "
                f"Did you mean '{suggested_name}'?"
            )
        }

    canonical_candidate_name = candidate_match["candidate_name"]
    candidate_email = candidate_match["email"]
    job_application_id = candidate_match["jobApplicationId"]

    if not candidate_email:
        return {
            "candidate_result": candidate_result,
            "candidate_name": canonical_candidate_name,
            "job_application_id": job_application_id,
            "final_response": (
                f"Candidate '{canonical_candidate_name}' was found, "
                "but the email address could not be found."
            )
        }

    if not job_application_id:
        return {
            "candidate_result": candidate_result,
            "candidate_name": canonical_candidate_name,
            "candidate_email": candidate_email,
            "final_response": (
                f"JobApplicationId was not found for {canonical_candidate_name}."
            )
        }

    print("\nCANDIDATE MATCHED:")
    print(canonical_candidate_name)
    print("Email:", candidate_email)
    print("JobApplicationId:", job_application_id)

    # ========================================================
    # INTERVIEWERDATA
    # ========================================================

    interviewer_body = build_agent_body(
        "INTERVIEWERDATA",
        {"RequisitionNumber": requisition_number}
    )

    print("\nCalling INTERVIEWERDATA...")

    interviewer_result = call_agent(
        "INTERVIEWERDATA",
        interviewer_body
    )

    print_agent_result(
        "INTERVIEWERDATA",
        interviewer_result
    )

    # ========================================================
    # RESOLVE INTERVIEWERS
    # ========================================================

    interviewer_match = resolve_interviewers(
        interviewer_result,
        interviewer_names
    )

    if interviewer_match["status"] == "NOT_FOUND":
        return {
            "candidate_result": candidate_result,
            "interviewer_result": interviewer_result,
            "waiting_for_user": True,
            "awaiting_confirmation": True,
            "confirmation_type": "interviewer",
            "interviewer_names": interviewer_names,
            "final_response": "I could not find the requested interviewer(s)."
        }

    matches = interviewer_match["matches"]

    canonical_interviewer_names = [
        item["actual_name"]
        for item in matches
    ]

    interviewer_emails = [
        item["email"]
        for item in matches
        if item.get("email")
    ]

    if not interviewer_emails:
        return {
            "candidate_result": candidate_result,
            "interviewer_result": interviewer_result,
            "final_response": "Interviewer email addresses could not be found."
        }

    if len(interviewer_emails) != len(canonical_interviewer_names):
        return {
            "candidate_result": candidate_result,
            "interviewer_result": interviewer_result,
            "interviewer_emails": interviewer_emails,
            "final_response": "I could not find email addresses for all requested interviewers."
        }

    print("\nMATCHED INTERVIEWERS:")
    print(canonical_interviewer_names)
    print("\nMATCHED EMAILS:")
    print(interviewer_emails)

    # ========================================================
    # INTERVIEWER AVAILABILITY
    # ========================================================

    availability_parameters = {
        "interviewer_emails": interviewer_emails,
        "date": start_datetime[:10],
        "meeting_duration_minutes": 30
    }

    availability_body = build_agent_body(
        "INTERVIEWER_AVAILABILITY",
        availability_parameters
    )

    print("\nCalling INTERVIEWER_AVAILABILITY...")

    try:
        availability_result = call_agent(
            "INTERVIEWER_AVAILABILITY",
            availability_body
        )
    except Exception as e:
        return {
            "candidate_result": candidate_result,
            "interviewer_result": interviewer_result,
            "final_response": f"Availability check failed: {str(e)}"
        }

    print_agent_result(
        "INTERVIEWER_AVAILABILITY",
        availability_result
    )

    # ========================================================
    # VERIFY REQUESTED SLOT
    # ========================================================

    if not is_requested_slot_available(
        availability_result,
        start_datetime,
        end_datetime
    ):
        common_slots = extract_common_slots(
            availability_result
        )

        return {
            "candidate_result": candidate_result,
            "candidate_email": candidate_email,
            "job_application_id": job_application_id,
            "interviewer_result": interviewer_result,
            "interviewer_emails": interviewer_emails,
            "availability_result": availability_result,
            "common_slots": common_slots,
            "waiting_for_user": False,
            "final_response": (
                f"The requested interview time {start_datetime} to "
                f"{end_datetime} is not available for all requested interviewer(s)."
            )
        }

    # ========================================================
    # SCHEDULING_TEAMS_MEETING
    # ========================================================

    scheduling_parameters = {
        "candidateName": canonical_candidate_name,
        "email": candidate_email,
        "startDateTime": start_datetime,
        "endDateTime": end_datetime,
        "subject": subject,
        "interviewers": canonical_interviewer_names,
        "interviewersEmail": interviewer_emails,
        "JobApplicationId": int(job_application_id)
    }

    scheduling_body = build_agent_body(
        "SCHEDULING_TEAMS_MEETING",
        scheduling_parameters
    )

    print("\nSCHEDULING_TEAMS_MEETING BODY")
    print(json.dumps(scheduling_body, indent=4, default=str))

    try:
        scheduling_result = call_agent(
            "SCHEDULING_TEAMS_MEETING",
            scheduling_body
        )
    except Exception as e:
        return {
            "candidate_result": candidate_result,
            "interviewer_result": interviewer_result,
            "availability_result": availability_result,
            "final_response": f"Interview scheduling failed: {str(e)}"
        }

    print_agent_result(
        "SCHEDULING_TEAMS_MEETING",
        scheduling_result
    )

    return {
        "candidate_result": candidate_result,
        "candidate_name": canonical_candidate_name,
        "candidate_email": candidate_email,
        "job_application_id": job_application_id,
        "interviewer_result": interviewer_result,
        "interviewers": canonical_interviewer_names,
        "interviewer_emails": interviewer_emails,
        "availability_result": availability_result,
        "scheduling_result": scheduling_result,
        "waiting_for_user": False,
        "final_response": "Interview scheduled successfully."
    }


# ============================================================
# EMAIL FLOW
# ============================================================

def email_flow(
    state: TaskState
):
    print("\n========================================")
    print("START EMAIL FLOW")
    print("========================================")

    candidate_name = state.get("candidate_name")
    requisition_number = state.get("requisition_number")
    email_type = state.get("email_type") or "other"

    missing = []

    if not candidate_name:
        missing.append("candidate_name")

    if not requisition_number:
        missing.append("requisition_number")

    if missing:
        return {
            "waiting_for_user": True,
            "missing_information": missing,
            "final_response": "Please provide the candidate name and requisition number."
        }

    candidate_body = build_agent_body(
        "CANDIDATEREQUISTION",
        {"RequisitionNumber": requisition_number}
    )

    print("\nCalling CANDIDATEREQUISTION...")

    candidate_result = call_agent(
        "CANDIDATEREQUISTION",
        candidate_body
    )

    print_agent_result(
        "CANDIDATEREQUISTION",
        candidate_result
    )

    # ========================================================
    # RESOLVE CANDIDATE USING SHARED RESOLVER
    # ========================================================

    candidate_match = resolve_candidate(
        candidate_result,
        candidate_name
    )

    if not candidate_match:
        return {
            "candidate_result": candidate_result,
            "waiting_for_user": False,
            "final_response": (
                f"I could not find a candidate matching '{candidate_name}' "
                f"in requisition {requisition_number}."
            )
        }

    if candidate_match["status"] == "SUGGEST":
        suggested_name = candidate_match["candidate_name"]

        return {
            "candidate_result": candidate_result,
            "waiting_for_user": True,
            "awaiting_confirmation": True,
            "confirmation_type": "candidate",
            "original_candidate_input": candidate_name,
            "suggested_candidate": suggested_name,
            "requisition_number": requisition_number,
            "email_type": email_type,
            "final_response": (
                f"I couldn't find an exact match for '{candidate_name}'. "
                f"Did you mean '{suggested_name}'?"
            )
        }

    canonical_candidate_name = candidate_match["candidate_name"]
    candidate_email = candidate_match["email"]
    job_application_id = candidate_match["jobApplicationId"]

    if not candidate_email:
        return {
            "candidate_result": candidate_result,
            "candidate_name": canonical_candidate_name,
            "job_application_id": job_application_id,
            "final_response": (
                f"Candidate '{canonical_candidate_name}' was found, "
                "but the email address could not be found."
            )
        }

    # ========================================================
    # EMAIL_HR
    # ========================================================

    email_parameters = {
        "Type": email_type,
        "Tone": "professional",
        "Email": candidate_email,
        "subject": state.get("subject"),
        "body": state.get("body"),
        "Note": state.get("note") or ""
    }

    email_body = build_agent_body(
        "EMAIL_HR",
        email_parameters
    )

    print("\nCalling EMAIL_HR...")

    email_result = call_agent(
        "EMAIL_HR",
        email_body
    )

    print_agent_result(
        "EMAIL_HR",
        email_result
    )

    # ========================================================
    # EXTRACT GENERATED EMAIL
    # ========================================================

    generated_email = extract_email_content(
        email_result
    )

    email_subject = generated_email.get(
        "subject"
    )

    email_text = generated_email.get(
        "body2"
    )

    print("\n========================================")
    print("GENERATED EMAIL")
    print("========================================")
    print("Subject:")
    print(email_subject)
    print("\nBody2:")
    print(email_text)

    if not email_subject:
        return {
            "candidate_result": candidate_result,
            "email_generation_result": email_result,
            "final_response": "EMAIL_HR did not return a subject."
        }

    if not email_text:
        return {
            "candidate_result": candidate_result,
            "email_generation_result": email_result,
            "final_response": "EMAIL_HR did not return a body."
        }

    # ========================================================
    # HREMAILSEND
    # ========================================================

    send_parameters = {
        "email": candidate_email,
        "subject": email_subject,
        "body": email_text
    }

    print("\nHREMAILSEND PARAMETERS")
    print(json.dumps(send_parameters, indent=4, default=str))

    send_body = build_agent_body(
        "HREMAILSEND",
        send_parameters
    )

    print("\nHREMAILSEND BODY")
    print(json.dumps(send_body, indent=4, default=str))

    try:
        send_result = call_agent(
            "HREMAILSEND",
            send_body
        )
    except Exception as e:
        return {
            "candidate_result": candidate_result,
            "candidate_name": canonical_candidate_name,
            "candidate_email": candidate_email,
            "job_application_id": job_application_id,
            "email_generation_result": email_result,
            "email_send_result": None,
            "waiting_for_user": False,
            "final_response": f"HREMAILSEND failed: {str(e)}"
        }

    print_agent_result(
        "HREMAILSEND",
        send_result
    )

    return {
        "candidate_result": candidate_result,
        "candidate_name": canonical_candidate_name,
        "candidate_email": candidate_email,
        "job_application_id": job_application_id,
        "email_generation_result": email_result,
        "email_send_result": send_result,
        "waiting_for_user": False,
        "awaiting_confirmation": False,
        "final_response": "Email sent successfully"
    }

# ============================================================
# LINKEDIN JOB DESCRIPTION FLOW
# ============================================================

def linkedin_job_desc_flow(
    state: TaskState
):

    print(
        "\n========================================"
    )

    print(
        "START LINKEDIN JOB DESCRIPTION FLOW"
    )

    print(
        "========================================"
    )

    job_description = (
        state.get(
            "job_description"
        )
    )

    # ========================================================
    # 1. CHECK JOB DESCRIPTION
    # ========================================================

    if not job_description:

        return {

            "waiting_for_user":
                True,

            "missing_information":
                [
                    "job_description"
                ],

            "final_response":
                (
                    "Please provide the job description "
                    "you want to post on LinkedIn."
                )
        }

    # ========================================================
    # 2. BUILD LINKEDIN AGENT PARAMETERS
    # ========================================================

    linkedin_parameters = {

        "jobDescription":
            job_description
    }

    # ========================================================
    # 3. BUILD AGENT BODY
    # ========================================================

    linkedin_body = build_agent_body(
        "LINKEDIN_JOB_DESC",
        linkedin_parameters
    )

    print(
        "\n========================================"
    )

    print(
        "LINKEDIN_JOB_DESC BODY"
    )

    print(
        "========================================"
    )

    print(
        json.dumps(
            linkedin_body,
            indent=4,
            default=str
        )
    )

    # ========================================================
    # 4. CALL LINKEDIN AGENT
    # ========================================================

    print(
        "\nCalling LINKEDIN_JOB_DESC..."
    )

    try:

        linkedin_result = call_agent(
            "LINKEDIN_JOB_DESC",
            linkedin_body
        )

    except Exception as e:

        print(
            "\nLINKEDIN_JOB_DESC ERROR:"
        )

        print(
            str(e)
        )

        return {

            "linkedin_result":
                None,

            "waiting_for_user":
                False,

            "final_response":
                (
                    "LinkedIn job posting failed: "
                    f"{str(e)}"
                )
        }

    # ========================================================
    # 5. PRINT RESULT
    # ========================================================

    print_agent_result(
        "LINKEDIN_JOB_DESC",
        linkedin_result
    )

    # ========================================================
    # 6. SUCCESS
    # ========================================================

    return {

        "linkedin_result":
            linkedin_result,

        "job_description":
            job_description,

        "waiting_for_user":
            False,

        "final_response":
            (
                "The job description was posted "
                "to LinkedIn successfully."
            )
    }


# ============================================================
# MAIN ORCHESTRATOR
# ============================================================

def orchestrate(
    state: TaskState
):
    task_type = state.get("task_type")

    print("\n========================================")
    print("ORCHESTRATOR")
    print("TASK:", task_type)
    print("========================================")

    if task_type == "SCREENING":
        return screening_flow(state)

    if task_type == "CHECK_AVAILABILITY":
        return availability_flow(state)

    if task_type == "SCHEDULE_INTERVIEW":
        return scheduling_flow(state)

    if task_type == "SEND_EMAIL":
        return email_flow(state)

    if task_type == "LINKEDIN_JOB_DESC":

        return linkedin_job_desc_flow(state)

    raise ValueError(
        f"Unsupported task type: {task_type}"
    )


# ============================================================
# EXTRACTION HELPERS
# ============================================================

def unwrap_agent_output(
    agent_result
):
    if not isinstance(agent_result, dict):
        return agent_result

    output = agent_result.get("output")

    if output is None:
        return agent_result

    if isinstance(output, str):
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return output

    return output


# ============================================================
# EXTRACT JOB APPLICATION IDS
# ============================================================

def extract_job_application_ids(
    agent_result,
    candidate_names
):
    output = agent_result.get("output")

    if output is None:
        return []

    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            return []

    result = output.get("result", {})
    requisitions = result.get("requisitions", [])

    requested_names = {
        str(name).strip().lower()
        for name in candidate_names
    }

    job_application_ids = []

    for candidate in requisitions:
        candidate_name = candidate.get("CandidateName")

        if not candidate_name:
            continue

        if candidate_name.strip().lower() in requested_names:
            job_application_id = candidate.get("JobApplicationId")

            if job_application_id:
                job_application_ids.append(
                    str(job_application_id)
                )

                print("\nCandidate matched:")
                print(candidate_name)
                print("JobApplicationId:", job_application_id)

    print("\nJobApplicationIds:")
    print(job_application_ids)

    return job_application_ids


# ============================================================
# EXTRACT CANDIDATE DATA
# ============================================================

def extract_candidate_data(
    agent_result,
    candidate_name
):
    output = agent_result.get("output")

    if output is None:
        return {}

    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            return {}

    result = output.get("result", {})
    requisitions = result.get("requisitions", [])

    target_name = str(candidate_name).strip().lower()

    for candidate in requisitions:
        candidate_name_from_api = candidate.get("CandidateName")

        if not candidate_name_from_api:
            continue

        if candidate_name_from_api.strip().lower() == target_name:
            return {
                "candidate_name": candidate_name_from_api,
                "email": candidate.get("Email"),
                "jobApplicationId": candidate.get("JobApplicationId")
            }

    return {}


# ============================================================
# EXTRACT INTERVIEWER EMAILS
# ============================================================

def extract_interviewer_emails(
    agent_result,
    interviewer_names
):
    output = agent_result.get("output")

    if output is None:
        return []

    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            return []

    interviewer_list = output.get("result", [])
    emails = []

    requested_names = {
        str(name).strip().lower()
        for name in interviewer_names
    }

    for interviewer in interviewer_list:
        display_name = str(
            interviewer.get("DisplayName", "")
        ).strip().lower()

        work_email = str(
            interviewer.get("WorkEmail", "")
        ).strip()

        if display_name in requested_names and work_email:
            emails.append(work_email)

    return list(dict.fromkeys(emails))


# ============================================================
# EXTRACT COMMON SLOTS
# ============================================================

def extract_common_slots(
    agent_result
):
    data = unwrap_agent_output(agent_result)

    if isinstance(data, dict):
        return (
            data.get("commonSlots")
            or data.get("common_slots")
            or data.get("meetingTimeSuggestions")
            or []
        )

    return []


# ============================================================
# CHECK REQUESTED TIME
# ============================================================

def is_requested_slot_available(
    availability_result,
    requested_start,
    requested_end
):
    try:
        output = availability_result.get("output")

        if not output:
            return False

        if isinstance(output, str):
            output = json.loads(output)

        common_slots = output.get("commonSlots", [])

        if not common_slots:
            return False

        requested_start_dt = datetime.fromisoformat(
            requested_start
        )

        requested_end_dt = datetime.fromisoformat(
            requested_end
        )

        for slot in common_slots:
            slot_start = slot.get("startDateTime")
            slot_end = slot.get("endDateTime")

            if not slot_start or not slot_end:
                continue

            # Keep timezone/offset information intact and normalize
            # long fractional seconds for Python fromisoformat().
            if "." in slot_start:
                prefix, fraction = slot_start.split(".", 1)
                fraction = fraction.split("+", 1)[0].split("-", 1)[0]
                suffix = ""
                if "+" in slot_start:
                    suffix = "+" + slot_start.split("+", 1)[1]
                elif "-" in fraction:
                    pass
                slot_start = prefix + "." + fraction[:6] + suffix

            if "." in slot_end:
                prefix, fraction = slot_end.split(".", 1)
                suffix = ""
                if "+" in slot_end:
                    fraction, tz = fraction.split("+", 1)
                    suffix = "+" + tz
                elif "-" in fraction:
                    fraction, tz = fraction.split("-", 1)
                    suffix = "-" + tz
                slot_end = prefix + "." + fraction[:6] + suffix

            slot_start_dt = datetime.fromisoformat(slot_start)
            slot_end_dt = datetime.fromisoformat(slot_end)

            if (
                slot_start_dt == requested_start_dt
                and
                slot_end_dt == requested_end_dt
            ):
                print("\nREQUESTED SLOT IS AVAILABLE")
                print("Requested:", requested_start, "to", requested_end)
                print("Matched:", slot_start, "to", slot_end)
                return True

        print("\nREQUESTED SLOT IS NOT AVAILABLE")
        return False

    except Exception as e:
        print("\nERROR CHECKING REQUESTED SLOT:")
        print(str(e))
        return False


# ============================================================
# EXTRACT EMAIL CONTENT
# ============================================================

def extract_email_content(
    agent_result
):
    output = agent_result.get("output")

    if not output:
        return {}

    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            return {}

    result = output.get("result", {})
    nested_result = result.get("result", {})
    emails = nested_result.get("emails", [])

    if not emails:
        return {}

    email_data = emails[0]

    return {
        "name": email_data.get("name"),
        "subject": email_data.get("subject"),
        "body1": email_data.get("body1"),
        "body2": email_data.get("body2")
    }
