import re
import time

import ollama

from ai.rag import retrieve_relevant_knowledge


# =========================
# CONSTANTS
# =========================

BUSINESS_FALLBACK = (
    "I don't have enough information to answer that yet."
)

MAX_LLM_HISTORY = 8


# =========================
# SYSTEM PROMPT
# =========================

SYSTEM_PROMPT = """
You are a Lead Nurturing AI Assistant.

Your job is to communicate with potential customers and understand
their requirements.

Rules:

1. Be professional, friendly, and concise.

2. Help the customer with their enquiry.

3. Ask only one qualification question at a time when a qualification
   question is actually needed.

4. Try to understand the customer's:
   interest
   budget
   timeline
   requirement

5. For business-specific questions, use ONLY the approved business
   knowledge provided in the BUSINESS KNOWLEDGE section.

6. Never invent business information, prices, course details,
   discounts, guarantees, services, policies, durations,
   certifications, placement guarantees, or offers.

7. Do not pressure the customer.

8. Keep responses easy to understand.

9. Distinguish between a customer QUESTION and a customer STATEMENT.

10. A customer statement about their interest, budget, timeline,
    requirement, career goal, situation, or contact availability
    does NOT require business knowledge.

11. When the customer provides qualification information,
    acknowledge it naturally.

12. Do not use the business-information fallback just because a
    qualification statement is not present in the knowledge base.

13. If the customer says when they are available to be contacted,
    acknowledge their availability naturally.

14. Never claim that you have scheduled a call, booked an appointment,
    sent a message, contacted the customer, or will contact the
    customer later unless the application actually provides that
    capability.

15. Never claim that the customer provided contact information unless
    that information is actually present in the conversation.

16. For business-information questions, answer the customer's question
    directly and stop after answering it.

17. Do not add unnecessary follow-up questions.

18. Do not repeat the same information multiple times in one response.

19. Give each important fact only once unless repetition is required
    to avoid misunderstanding.

20. If requested business information is unavailable, do not invent it.

21. Do not use Markdown bullet symbols such as *, -, or • in the
    final response. When listing multiple items, write each item on
    its own separate line without any bullet symbol.

22. Never ask for a qualification field that already has a value in
    CURRENT STRUCTURED QUALIFICATION.

23. When a qualification statement needs a follow-up question, ask only
    the next missing qualification field in this order:
    interest, budget, timeline, requirement.

24. NEVER create a price, discount, offer, duration, course,
    certification, placement promise, refund policy, schedule,
    training feature, or service unless that exact information
    appears in CURRENT APPROVED BUSINESS KNOWLEDGE.

25. If CURRENT APPROVED BUSINESS KNOWLEDGE does not support a business
    claim, do not make that claim.

26. Previous assistant messages are NOT approved business knowledge.
    Never repeat a business fact merely because an earlier assistant
    message said it.

27. Conversation history may be used to understand context only.
    It must never be treated as a source of business facts.

28. CURRENT STRUCTURED QUALIFICATION may be used only for customer
    information such as interest, budget, timeline, and requirement.
    It is not a source for business prices, offers, discounts,
    course details, or policies.

Correct list format:

Amazon EC2
Amazon S3
IAM
VPC
EFS
RDS
Elastic Load Balancer
CloudWatch
"""


# =========================
# RESPONSE FORMAT CLEANER
# =========================

def clean_response_format(text: str) -> str:

    if not text:
        return text

    cleaned_lines = []

    for line in text.splitlines():

        cleaned_line = re.sub(
            r"^\s*[\*\-•]\s+",
            "",
            line
        )

        cleaned_line = cleaned_line.replace(
            "**",
            ""
        )

        cleaned_lines.append(
            cleaned_line.rstrip()
        )

    return "\n".join(
        cleaned_lines
    ).strip()


# =========================
# HELPER - NORMALIZE TEXT
# =========================

def normalize_text(text: str) -> str:

    if not text:
        return ""

    return " ".join(
        text.lower().strip().split()
    )


# =========================
# CERTIFICATION GUARD
# =========================

def get_certification_response(
    prompt: str
):

    prompt_lower = normalize_text(prompt)

    certification_words = [
        "certification",
        "certificate",
        "international certificate",
        "international certification",
        "certification exam",
        "certification examination",
        "exam preparation",
        "examination preparation",
    ]

    is_certification_message = any(
        word in prompt_lower
        for word in certification_words
    )

    if not is_certification_message:
        return None

    # AWS
    if (
        "aws" in prompt_lower
        or "amazon" in prompt_lower
    ):

        return (
            "Yes. Skillect provides training and examination "
            "preparation support for relevant official AWS "
            "certification examinations. To earn the official AWS "
            "certification, you must pass the relevant official AWS "
            "certification examination. Skillect does not directly "
            "issue the official AWS certification."
        )

    # AZURE
    if (
        "azure" in prompt_lower
        or "microsoft" in prompt_lower
    ):

        return (
            "Yes. Skillect provides training and examination "
            "preparation support for relevant official Microsoft "
            "Azure certification examinations. To earn the official "
            "Microsoft Azure certification, you must pass the relevant "
            "official Microsoft certification examination. Skillect "
            "does not directly issue the official Microsoft Azure "
            "certification."
        )

    # GENERAL
    return (
        "Skillect provides training and examination preparation "
        "support for relevant AWS and Microsoft Azure certification "
        "examinations. Official certifications require students to "
        "pass the relevant official AWS or Microsoft certification "
        "examination. Skillect does not directly issue these official "
        "international certifications."
    )


# =========================
# CONTACT AVAILABILITY GUARD
# =========================

def get_contact_availability_response(
    prompt: str
):

    prompt_lower = normalize_text(prompt)

    contact_phrases = [
        "contact me",
        "call me",
        "reach me",
        "available for a call",
        "available to talk",
        "available to speak",
        "free this week",
        "free next week",
        "free tomorrow",
        "free on",
        "free after",
    ]

    is_contact_availability = any(
        phrase in prompt_lower
        for phrase in contact_phrases
    )

    if not is_contact_availability:
        return None

    if "this week" in prompt_lower:

        return (
            "Sure. You're available to be contacted this week. "
            "Please provide your preferred day and time."
        )

    if "next week" in prompt_lower:

        return (
            "Sure. You're available to be contacted next week. "
            "Please provide your preferred day and time."
        )

    if "tomorrow" in prompt_lower:

        return (
            "Sure. You're available to be contacted tomorrow. "
            "Please provide your preferred time."
        )

    return (
        "Sure. I've noted your availability. "
        "Please provide your preferred day and time."
    )


# =========================
# EXPLICIT INTEREST GUARD
# =========================

def get_explicit_interest_response(
    prompt: str
):

    prompt_lower = normalize_text(prompt)

    interest_phrases = [
        "i am interested in",
        "i'm interested in",
        "im interested in",
        "my interest is",
        "actually i am interested in",
        "actually i'm interested in",
        "actually im interested in",
        "i want to learn",
        "i want to study",
        "i want to join",
        "i would like to learn",
        "i would like to join",
    ]

    is_interest_statement = any(
        phrase in prompt_lower
        for phrase in interest_phrases
    )

    if not is_interest_statement:
        return None

    if (
        "aws" in prompt_lower
        or "amazon" in prompt_lower
    ):

        return (
            "Great. You're interested in "
            "AWS Cloud Engineering."
        )

    if "azure" in prompt_lower:

        return (
            "Great. You're interested in "
            "Azure Cloud Engineering."
        )

    if "cloud" in prompt_lower:

        return (
            "Great. You're interested in "
            "Cloud Computing."
        )

    if "python" in prompt_lower:

        return (
            "Great. You're interested in Python."
        )

    return None


# =========================
# REQUIREMENT ACKNOWLEDGEMENT
# =========================

def get_requirement_response(
    prompt: str,
    qualification=None
):

    prompt_lower = normalize_text(prompt)

    # =========================
    # CAREER SWITCH
    # =========================

    career_switch_phrases = [
        "career switch",
        "switch career",
        "switch careers",
        "switch my career",
        "switching career",
        "switching careers",
        "career change",
        "change my career",
    ]

    if any(
        phrase in prompt_lower
        for phrase in career_switch_phrases
    ):

        return (
            "Got it. You're looking to make "
            "a career switch."
        )

    # =========================
    # SKILL DEVELOPMENT
    # =========================

    skill_phrases = [
        "improve my skills",
        "skill development",
        "develop my skills",
        "upgrade my skills",
        "upskill",
    ]

    if any(
        phrase in prompt_lower
        for phrase in skill_phrases
    ):

        return (
            "Got it. You're looking to improve "
            "your skills."
        )

    # =========================
    # JOB
    # =========================
    #
    # IMPORTANT:
    # These phrases match qualification.py.
    # This prevents qualification statements
    # from unnecessarily reaching Ollama.
    # =========================

    job_phrases = [
        "i need a job",
        "i want a job",
        "i want to get a job",
        "i need to get a job",
        "i would like to get a job",
        "i'm trying to get a job",
        "im trying to get a job",
        "i am trying to get a job",
        "my goal is to get a job",
        "my main goal is to get a job",
        "goal is to get a job",
        "get a job",
        "getting a job",
        "find a job",
        "finding a job",
        "i am looking for a job",
        "i'm looking for a job",
        "im looking for a job",
        "looking for a job",
        "i need this for a job",
        "i want this for a job",
        "i need this course for a job",
        "i want this course for a job",
        "job placement",
        "placement assistance",
        "placement opportunity",
        "job opportunity",
        "job opportunities",
        "employment",
        "employment opportunity",
        "employment opportunities",
        "career opportunity",
        "career opportunities",
        "career growth",
        "build my career",
        "start my career",
        "career goal",
    ]

    if any(
        phrase in prompt_lower
        for phrase in job_phrases
    ):

        return (
            "Got it. Your current requirement "
            "is a job."
        )

    return None


# =========================
# QUALIFICATION STATEMENT GUARD
# =========================

def get_qualification_statement_response(
    prompt: str,
    qualification=None
):

    if not qualification:
        return None

    prompt_lower = normalize_text(prompt)

    interest = qualification.get(
        "interest"
    )

    budget = qualification.get(
        "budget"
    )

    timeline = qualification.get(
        "timeline"
    )

    requirement = qualification.get(
        "requirement"
    )

    # =========================
    # BUDGET STATEMENT
    # =========================

    budget_phrases = [
        "my budget",
        "i have a budget",
        "i can spend",
        "i can afford",
        "my maximum budget",
        "my max budget",
    ]

    is_budget_statement = any(
        phrase in prompt_lower
        for phrase in budget_phrases
    )

    if (
        is_budget_statement
        and budget is not None
    ):

        acknowledgement = (
            f"Got it. Your budget is "
            f"₹{budget:,}."
        )

        if not interest:

            return (
                f"{acknowledgement} "
                "What is your interest in "
                "cloud engineering?"
            )

        if not timeline:

            return (
                f"{acknowledgement} "
                "When are you planning to "
                "start the course?"
            )

        if not requirement:

            return (
                f"{acknowledgement} "
                "What is your main goal for "
                "taking the course?"
            )

        return acknowledgement

    # =========================
    # TIMELINE STATEMENT
    # =========================

    timeline_phrases = [
        "i want to start",
        "i can start",
        "i would like to start",
        "i'm planning to start",
        "i am planning to start",
        "i plan to start",
        "i need to start",
        "start immediately",
        "start now",
        "right now",
        "this month",
        "next month",
        "as soon as possible",
        "asap",
    ]

    is_timeline_statement = any(
        phrase in prompt_lower
        for phrase in timeline_phrases
    )

    if (
        is_timeline_statement
        and timeline
    ):

        acknowledgement = (
            f"Got it. You're planning to start "
            f"{timeline.lower()}."
        )

        if not interest:

            return (
                f"{acknowledgement} "
                "What is your interest in "
                "cloud engineering?"
            )

        if budget is None:

            return (
                f"{acknowledgement} "
                "What is your budget for "
                "the course?"
            )

        if not requirement:

            return (
                f"{acknowledgement} "
                "What is your main goal for "
                "taking the course?"
            )

        return acknowledgement

    return None


# =========================
# QUALIFICATION MEMORY GUARD
# =========================

def get_qualification_memory_response(
    prompt: str,
    qualification=None
):

    if not qualification:
        return None

    prompt_lower = normalize_text(prompt)

    # =========================
    # CURRENT INTEREST
    # =========================

    interest_questions = [
        "what is my current interest",
        "what's my current interest",
        "what is my interest",
        "what's my interest",
        "which course am i interested in",
        "which course i am interested in",
        "what course am i interested in",
    ]

    if any(
        phrase in prompt_lower
        for phrase in interest_questions
    ):

        interest = qualification.get(
            "interest"
        )

        if interest:

            return (
                f"Your current interest is "
                f"{interest}."
            )

        return (
            "You haven't provided your current "
            "course interest yet."
        )

    # =========================
    # CURRENT BUDGET
    # =========================

    budget_questions = [
        "what is my budget",
        "what's my budget",
        "what is my current budget",
        "what's my current budget",
        "how much is my budget",
    ]

    if any(
        phrase in prompt_lower
        for phrase in budget_questions
    ):

        budget = qualification.get(
            "budget"
        )

        if budget is not None:

            return (
                f"Your current budget is "
                f"₹{budget:,}."
            )

        return (
            "You haven't provided your budget yet."
        )

    # =========================
    # CURRENT TIMELINE
    # =========================

    timeline_questions = [
        "what is my timeline",
        "what's my timeline",
        "what is my current timeline",
        "what's my current timeline",
        "when do i want to start",
        "when am i planning to start",
    ]

    if any(
        phrase in prompt_lower
        for phrase in timeline_questions
    ):

        timeline = qualification.get(
            "timeline"
        )

        if timeline:

            return (
                f"Your current timeline is "
                f"{timeline}."
            )

        return (
            "You haven't provided your timeline yet."
        )

    # =========================
    # CURRENT REQUIREMENT
    # =========================

    requirement_questions = [
        "what is my requirement",
        "what's my requirement",
        "what is my current requirement",
        "what's my current requirement",
        "what do i need",
        "what is my goal",
        "what's my goal",
    ]

    if any(
        phrase in prompt_lower
        for phrase in requirement_questions
    ):

        requirement = qualification.get(
            "requirement"
        )

        if requirement:

            return (
                f"Your current requirement is "
                f"{requirement}."
            )

        return (
            "You haven't provided your requirement yet."
        )

    return None


# =========================
# BUILD RAG QUERY
# =========================

def build_retrieval_query(
    prompt: str,
    history=None
) -> str:

    prompt_lower = normalize_text(prompt)

    current_mentions_aws = (
        "aws" in prompt_lower
        or "amazon" in prompt_lower
    )

    current_mentions_azure = (
        "azure" in prompt_lower
    )

    current_has_explicit_provider = (
        current_mentions_aws
        or current_mentions_azure
    )

    # If the customer explicitly names a provider,
    # retrieve only for the current request.
    if current_has_explicit_provider:
        return prompt

    retrieval_parts = []

    if history:

        recent_user_messages = [
            item.message
            for item in history
            if item.role in (
                "lead",
                "user"
            )
        ][-3:]

        retrieval_parts.extend(
            recent_user_messages
        )

    retrieval_parts.append(
        prompt
    )

    return " ".join(
        retrieval_parts
    )


# =========================
# BUILD QUALIFICATION CONTEXT
# =========================

def build_qualification_context(
    qualification=None
) -> str:

    if not qualification:

        return (
            "No structured qualification data "
            "is currently available."
        )

    return f"""
Interest:
{qualification.get("interest")}

Budget:
{qualification.get("budget")}

Timeline:
{qualification.get("timeline")}

Requirement:
{qualification.get("requirement")}
""".strip()


# =========================
# ASK AI
# =========================

def ask_ai(
    prompt: str,
    history=None,
    qualification=None
) -> str:

    total_llm_start = time.perf_counter()

    # =========================
    # 1. CERTIFICATION GUARD
    # =========================

    certification_response = (
        get_certification_response(
            prompt
        )
    )

    if certification_response is not None:

        return clean_response_format(
            certification_response
        )

    # =========================
    # 2. CONTACT GUARD
    # =========================

    contact_response = (
        get_contact_availability_response(
            prompt
        )
    )

    if contact_response is not None:

        return clean_response_format(
            contact_response
        )

    # =========================
    # 3. EXPLICIT INTEREST GUARD
    # =========================

    interest_response = (
        get_explicit_interest_response(
            prompt
        )
    )

    if interest_response is not None:

        return clean_response_format(
            interest_response
        )

    # =========================
    # 4. REQUIREMENT GUARD
    # =========================
    #
    # IMPORTANT:
    # Run this before Ollama.
    #
    # Example:
    # "My main goal is to get a job"
    #
    # will be handled here instead of allowing
    # the LLM to invent course/discount details.
    # =========================

    requirement_response = (
        get_requirement_response(
            prompt,
            qualification
        )
    )

    if requirement_response is not None:

        return clean_response_format(
            requirement_response
        )

    # =========================
    # 5. QUALIFICATION STATEMENT
    # =========================

    qualification_statement_response = (
        get_qualification_statement_response(
            prompt,
            qualification
        )
    )

    if qualification_statement_response is not None:

        return clean_response_format(
            qualification_statement_response
        )

    # =========================
    # 6. QUALIFICATION MEMORY
    # =========================

    qualification_response = (
        get_qualification_memory_response(
            prompt,
            qualification
        )
    )

    if qualification_response is not None:

        return clean_response_format(
            qualification_response
        )

    # =========================
    # 7. BUILD RAG QUERY
    # =========================

    retrieval_query = build_retrieval_query(
        prompt,
        history
    )

    # =========================
    # 8. RETRIEVE KNOWLEDGE
    # =========================

    rag_start = time.perf_counter()

    business_knowledge = (
        retrieve_relevant_knowledge(
            retrieval_query
        )
    )

    rag_time = (
        time.perf_counter()
        - rag_start
    )

    print(
        f"RAG TIME: "
        f"{rag_time:.3f} seconds"
    )

    if business_knowledge is None:
        business_knowledge = ""

    knowledge_found = bool(
        business_knowledge.strip()
    )

    if not knowledge_found:

        business_knowledge = (
            "NO RELEVANT APPROVED "
            "BUSINESS INFORMATION FOUND."
        )

    # =========================
    # 9. BUILD QUALIFICATION CONTEXT
    # =========================

    qualification_context = (
        build_qualification_context(
            qualification
        )
    )

    # =========================
    # 10. BUILD SYSTEM CONTEXT
    # =========================

    prompt_build_start = (
        time.perf_counter()
    )

    system_content = f"""
{SYSTEM_PROMPT}

=========================
CURRENT STRUCTURED QUALIFICATION
=========================

{qualification_context}

=========================
CURRENT APPROVED BUSINESS KNOWLEDGE
=========================

{business_knowledge}

=========================
END OF APPROVED BUSINESS KNOWLEDGE
=========================

STRICT GROUNDING RULES:

1. CURRENT APPROVED BUSINESS KNOWLEDGE is the only authoritative
   source for business facts.

2. CURRENT STRUCTURED QUALIFICATION is the authoritative source
   only for the customer's:
   interest
   budget
   timeline
   requirement

3. If conversation history conflicts with CURRENT STRUCTURED
   QUALIFICATION, use CURRENT STRUCTURED QUALIFICATION.

4. Conversation history is NOT an approved source of business facts.

5. Previous assistant responses are NOT an approved source of
   business facts.

6. Never repeat a business claim simply because an earlier assistant
   response said it.

7. For a business-information question, answer ONLY the information
   specifically requested.

8. Do not substitute another available business fact when the
   requested fact is unavailable.

9. If the specifically requested information exists in CURRENT
   APPROVED BUSINESS KNOWLEDGE, answer directly.

10. If all specifically requested business information is unavailable,
    answer exactly:

    "{BUSINESS_FALLBACK}"

11. Never invent business facts.

12. Qualification statements are not business-information questions.

13. A qualification statement should be acknowledged naturally.

14. Do not change qualification merely because a customer asks a
    factual question about AWS or Azure.

15. If the CURRENT message explicitly mentions AWS, use only relevant
    AWS information from CURRENT APPROVED BUSINESS KNOWLEDGE.

16. If the CURRENT message explicitly mentions Azure, use only relevant
    Azure information from CURRENT APPROVED BUSINESS KNOWLEDGE.

17. A saved interest must not override a provider explicitly named in
    the current business question.

18. Do not repeat unrelated conversation history.

19. Do not mention information the customer did not ask for.

20. Do not add unnecessary follow-up questions.

21. After answering a business-information question, STOP.

22. Keep the final response concise and direct.

23. Do not use Markdown bullet symbols such as *, -, or •
    in the final response.

24. If multiple items must be listed, put each item on a separate
    line without a bullet symbol.

25. Never ask for interest, budget, timeline, or requirement when
    that field already has a value in CURRENT STRUCTURED QUALIFICATION.

26. CLOSED-BOOK BUSINESS RULE:

    For business-information questions, do NOT use pretrained
    knowledge, general AWS knowledge, general Azure knowledge,
    assumptions, or information remembered from previous assistant
    responses.

27. Every factual business claim in the final response must be
    directly supported by CURRENT APPROVED BUSINESS KNOWLEDGE.

28. If a factual detail is not explicitly present in CURRENT APPROVED
    BUSINESS KNOWLEDGE, omit that detail completely.

29. NEVER invent:
    prices
    discounts
    special offers
    course duration
    course availability
    certification names
    examination fees
    guarantees
    placement guarantees
    refund policies
    schedules
    services
    course features

30. Do not expand approved facts with outside explanations.

31. Do not invent teaching methods, labs, projects,
    production architectures, troubleshooting activities,
    optimization activities, guarantees, outcomes,
    or additional course features.

32. Do not mention certification information unless the CURRENT
    customer message specifically asks about certification,
    certificate, or a certification examination.

33. Never invent or name a specific AWS or Microsoft certification,
    certification level, certification code, examination fee,
    examination date, validity period, or passing score unless that
    exact information exists in CURRENT APPROVED BUSINESS KNOWLEDGE.

34. Before producing the final response, silently inspect every
    business factual claim.

35. For every business factual claim, ask internally:
    "Can this exact fact be supported by CURRENT APPROVED
    BUSINESS KNOWLEDGE?"

36. If the answer is no, REMOVE that claim.

37. Never infer a discount from the customer's budget.

38. Never infer a course recommendation merely from the customer's
    qualification.

39. Never say that a discounted course is available unless CURRENT
    APPROVED BUSINESS KNOWLEDGE explicitly says so.

40. Never say that a discount is unavailable for another course unless
    CURRENT APPROVED BUSINESS KNOWLEDGE explicitly says so.

41. Never invent an Azure course because Azure appears somewhere in
    conversation history.

42. Never invent an AWS course because AWS appears somewhere in
    conversation history.

43. Customer budget means only the amount the customer can spend.
    It does NOT mean that a business course exists at that price.

44. Customer requirement means only the customer's goal.
    It does NOT prove that the business guarantees that outcome.

45. If the customer says they want a job, acknowledge that goal.
    Do not promise employment or placement.

46. Prefer a short complete answer using supported information.

47. Do not add extra information merely to make the answer longer.
"""

    # =========================
    # 11. START MESSAGES
    # =========================

    messages = [
        {
            "role": "system",
            "content": system_content
        }
    ]

    # =========================
    # 12. ADD LIMITED HISTORY
    # =========================

    if history:

        recent_history = (
            history[
                -MAX_LLM_HISTORY:
            ]
        )

        print(
            "\n------------------------------"
        )

        print(
            "LLM HISTORY OPTIMIZATION"
        )

        print(
            "------------------------------"
        )

        print(
            f"TOTAL STORED HISTORY: "
            f"{len(history)}"
        )

        print(
            f"HISTORY SENT TO LLAMA: "
            f"{len(recent_history)}"
        )

        for item in recent_history:

            # DATABASE ROLE -> OLLAMA ROLE

            if item.role in (
                "lead",
                "user"
            ):

                ollama_role = "user"

            elif item.role in (
                "ai",
                "assistant"
            ):

                ollama_role = "assistant"

            else:
                continue

            messages.append(
                {
                    "role": ollama_role,
                    "content": item.message
                }
            )

    else:

        print(
            "\n------------------------------"
        )

        print(
            "LLM HISTORY OPTIMIZATION"
        )

        print(
            "------------------------------"
        )

        print(
            "TOTAL STORED HISTORY: 0"
        )

        print(
            "HISTORY SENT TO LLAMA: 0"
        )

    # =========================
    # 13. CURRENT QUALIFICATION
    # =========================

    current_interest = (
        qualification.get(
            "interest"
        )
        if qualification
        else None
    )

    current_budget = (
        qualification.get(
            "budget"
        )
        if qualification
        else None
    )

    current_timeline = (
        qualification.get(
            "timeline"
        )
        if qualification
        else None
    )

    current_requirement = (
        qualification.get(
            "requirement"
        )
        if qualification
        else None
    )

    # =========================
    # 14. REINFORCE CURRENT REQUEST
    # =========================

    messages.append(
        {
            "role": "system",
            "content": f"""
CURRENT CUSTOMER MESSAGE:

{prompt}

CURRENT STRUCTURED QUALIFICATION:

Interest: {current_interest}
Budget: {current_budget}
Timeline: {current_timeline}
Requirement: {current_requirement}

CURRENT APPROVED BUSINESS KNOWLEDGE:

{business_knowledge}

FINAL RESPONSE RULES:

1. Answer only the CURRENT customer message.

2. Use CURRENT APPROVED BUSINESS KNOWLEDGE as the ONLY source
   for business facts.

3. Previous assistant messages are not business knowledge.

4. Conversation history is context only.

5. Never copy an unsupported business claim from conversation history.

6. If the specifically requested business fact is unavailable,
   do not replace it with other available facts.

7. If the requested business information is unavailable, reply exactly:

   "{BUSINESS_FALLBACK}"

8. If AWS is explicitly named in the current question,
   use only approved AWS information.

9. If Azure is explicitly named in the current question,
   use only approved Azure information.

10. The customer's saved qualification interest does not override
    the provider named in the current question.

11. Asking a factual question about AWS or Azure does not
    automatically change the saved interest.

12. Do not repeat unrelated history.

13. Do not invent information.

14. Do not add unnecessary follow-up questions.

15. Keep the response concise.

16. Do not use *, -, •, or any Markdown bullet symbol.

17. When listing multiple items, put each item on its own
    separate line without a bullet symbol.

18. Never ask for a qualification field that already has
    a value in CURRENT STRUCTURED QUALIFICATION.

19. Never invent prices.

20. Never invent discounts.

21. Never invent course durations.

22. Never invent course availability.

23. Never invent placement guarantees.

24. Never invent offers or promotions.

25. Never infer business facts from the customer's budget.

26. Never infer business facts from the customer's requirement.

27. If the customer wants a job, that means only that their
    requirement is Job. It does not mean placement is guaranteed.

28. Every business factual claim must be supported by the
    CURRENT APPROVED BUSINESS KNOWLEDGE above.

29. If a detail is not supported by CURRENT APPROVED BUSINESS
    KNOWLEDGE, remove it.

30. Before answering, silently check every business factual
    statement against CURRENT APPROVED BUSINESS KNOWLEDGE.
"""
        }
    )

    # =========================
    # 15. ADD CURRENT MESSAGE
    # =========================

    messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    prompt_build_time = (
        time.perf_counter()
        - prompt_build_start
    )

    print(
        f"PROMPT BUILD TIME: "
        f"{prompt_build_time:.3f} seconds"
    )

    # =========================
    # 16. GENERATE AI RESPONSE
    # =========================

    try:

        print(
            "\n------------------------------"
        )

        print(
            "OLLAMA GENERATION"
        )

        print(
            "------------------------------"
        )

        ollama_start = (
            time.perf_counter()
        )

        response = ollama.chat(
            model="llama3.2:3b",
            messages=messages,
            options={
                "temperature": 0,
                "num_predict": 150
            }
        )

        ollama_time = (
            time.perf_counter()
            - ollama_start
        )

        print(
            f"OLLAMA CHAT TIME: "
            f"{ollama_time:.3f} seconds"
        )

        ai_message = (
            response[
                "message"
            ][
                "content"
            ]
        )

        if (
            not ai_message
            or not ai_message.strip()
        ):

            raise RuntimeError(
                "Ollama returned an empty response"
            )

        # =========================
        # CLEAN RESPONSE FORMAT
        # =========================

        ai_message = (
            clean_response_format(
                ai_message
            )
        )

        total_llm_time = (
            time.perf_counter()
            - total_llm_start
        )

        print(
            f"TOTAL LLM TIME: "
            f"{total_llm_time:.3f} seconds"
        )

        return ai_message

    # =========================
    # OLLAMA CONNECTION FAILURE
    # =========================

    except ConnectionError as error:

        print(
            f"Ollama connection error: "
            f"{error}"
        )

        raise RuntimeError(
            "AI service is temporarily unavailable"
        ) from error

    # =========================
    # OTHER OLLAMA FAILURE
    # =========================

    except Exception as error:

        print(
            f"Ollama AI error: "
            f"{type(error).__name__}: "
            f"{error}"
        )

        raise RuntimeError(
            "AI service is temporarily unavailable"
        ) from error