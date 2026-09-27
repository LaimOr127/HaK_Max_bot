from __future__ import annotations

from enum import StrEnum


class BusinessForm(StrEnum):
    IP = "ip"
    OOO = "ooo"
    SELF_EMPLOYED = "self_employed"


class BusinessStage(StrEnum):
    NEW = "new"
    LT1 = "lt1"
    ONE_TO_THREE = "1_3"
    GT3 = "gt3"


class EmployeeBucket(StrEnum):
    ONE = "1"
    TWO_TO_FIFTEEN = "2_15"
    SIXTEEN_TO_HUNDRED = "16_100"
    OVER_HUNDRED = "100_plus"


class SphereCategory(StrEnum):
    FOODSERVICE = "foodservice"
    RETAIL = "retail"
    HOUSEHOLD_SERVICES = "household_services"
    PROFESSIONAL = "professional"
    IT_DIGITAL = "it_digital"
    MANUFACTURING = "manufacturing"
    CONSTRUCTION_REPAIR = "construction_repair"
    BEAUTY_HEALTH = "beauty_health"
    HEALTH = "health"
    EDUCATION = "education"
    TRANSPORT_LOGISTICS = "transport_logistics"
    TOURISM = "tourism"
    OTHER = "other"


class MspCategory(StrEnum):
    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"


class ProfileSource(StrEnum):
    FNS = "fns"
    MANUAL = "manual"


class SupportLevel(StrEnum):
    FEDERAL = "federal"
    REGIONAL = "regional"


class ConversationState(StrEnum):
    IDLE = "IDLE"
    WELCOME = "WELCOME"
    AWAITING_INN = "AWAITING_INN"
    AWAITING_EMPLOYEE_BUCKET = "AWAITING_EMPLOYEE_BUCKET"
    AWAITING_STAGE = "AWAITING_STAGE"
    MANUAL_REGION = "MANUAL_REGION"
    MANUAL_BUSINESS_FORM = "MANUAL_BUSINESS_FORM"
    MANUAL_SPHERE = "MANUAL_SPHERE"
    MANUAL_STAGE = "MANUAL_STAGE"
    MANUAL_EMPLOYEES = "MANUAL_EMPLOYEES"
    CONFIRM_PROFILE = "CONFIRM_PROFILE"
    RESET_CONFIRM = "RESET_CONFIRM"
    FEEDBACK_REASON = "FEEDBACK_REASON"
    FEEDBACK_TEXT = "FEEDBACK_TEXT"
    ZERO_FEEDBACK_TEXT = "ZERO_FEEDBACK_TEXT"
    INVESTOR_NAME = "INVESTOR_NAME"
    INVESTOR_CONTACT = "INVESTOR_CONTACT"
    READY = "READY"


class MatchStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    NEEDS_MORE_INFO = "NEEDS_MORE_INFO"
    INELIGIBLE = "INELIGIBLE"


class CompanyLookupStatus(StrEnum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    TEMPORARILY_UNAVAILABLE = "TEMPORARILY_UNAVAILABLE"


class FeedbackType(StrEnum):
    NOT_ELIGIBLE = "not_eligible"
    OUTDATED = "outdated"
    OTHER = "other"


class InvestorPromptState(StrEnum):
    NOT_SHOWN = "not_shown"
    DECLINED = "declined"
    INTERESTED = "interested"


class AnalyticsEventType(StrEnum):
    BOT_STARTED = "bot_started"
    ONBOARDING_STARTED = "onboarding_started"
    MANUAL_ONBOARDING_STARTED = "manual_onboarding_started"
    INN_LOOKUP_STARTED = "inn_lookup_started"
    INN_LOOKUP_SUCCESS = "inn_lookup_success"
    INN_LOOKUP_NOT_FOUND = "inn_lookup_not_found"
    INN_LOOKUP_FAILED = "inn_lookup_failed"
    PROFILE_CONFIRMED = "profile_confirmed"
    RECOMMENDATIONS_SHOWN = "recommendations_shown"
    ZERO_RECOMMENDATIONS = "zero_recommendations"
    MEASURE_DETAILS_OPENED = "measure_details_opened"
    CHECKLIST_ADDED = "checklist_added"
    CHECKLIST_DOCUMENT_DONE = "checklist_document_done"
    FEEDBACK_SUBMITTED = "feedback_submitted"
    ZERO_RESULT_FEEDBACK = "zero_result_feedback"
    INVESTOR_INTEREST_SUBMITTED = "investor_interest_submitted"
