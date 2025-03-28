# Refactor code
1. Remove folder routers if not being used
2. Include API versioning like /api/v1
4. Businness logic should be in service not in repository
```python
async def get_training_stats(self, user_id: str) -> Dict:
        training_plan_ids = await self._get_user_assignments(user_id)

        total_simulations = 0
        completed_simulations = 0
        total_score = 0
        highest_score = 0

        for tp_id in training_plan_ids:
            plan = await self.db.training_plans.find_one({"_id": tp_id})
            if not plan:
                continue

            for module_id in plan.get("moduleIds", []):
                module = await self.db.modules.find_one({"_id": module_id})
                if not module:
                    continue

                for sim_id in module.get("simulationIds", []):
                    simulation = await self.db.simulations.find_one({"_id": sim_id})
                    if not simulation:
                        continue
```
5. Move tgas in APIRouter()
```python
@router.post("/attempts/fetch", tags=["Playback", "Read", "List"])
####
router = APIRouter()
```
6. move all prompts to a common file, get_llm function to get AzureChatCompletion, move deepgramUrl to config
```python
try:
    history = ChatHistory()

    # Add system message
    history.add_system_message(
        "Convert the following text into a natural conversation between a user and an assistant. "
        "Return the result as a JSON object with a 'script' array containing objects with 'role' and "
        "'message' fields. The conversation should flow naturally and make sense. There are only two "
        "roles 'Customer' and 'Trainee' in the conversation. The user is always the Customer and the "
        "Trainee is always the assistant.")
###########################
 # Add Azure OpenAI service
self.chat_completion = AzureChatCompletion(
    service_id="azure_gpt4",
    deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME,
    endpoint=AZURE_OPENAI_BASE_URL,
    api_key=AZURE_OPENAI_KEY)
self.kernel.add_service(self.chat_completion)
#########################
async def transcribe_audio(self, audio_content: bytes) -> str:
"""
Transcribes audio content using Deepgram API
"""
url = 'https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&diarize=true'
headers = {
    'Authorization': f'Token {self.api_key}',
    'Content-Type': 'audio/wav'
}
```
7. have a abstraction over kernal ChatHistory()
8. Proper structure
    1. Controller - calls service, return Jsonreponse with status
    2. Service - Has businessLogic and calls Repository for data, returns data to controller
    3. Repository - All DB interactions, calls DB to get data and return to service
9. remove unused import, deprecated function.
# Db initiation directly called in service
1. call get_instance classmethod instead of Database()
```python
@classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
```
# CORS middleware setup
# Error Handling
Make request body validated with pydantic model not like Dict[str,str]
```python
sync def fetch_user_training_stats(request: `Dict[str, str])`:
    return await controller.get_training_data(request.get("id"))
```
# Audit Log

An audit log helps monitor and log activities such as user actions, API requests, or changes to data. This is useful for debugging, security, and compliance purposes.

For example, you can log details like:
- Which stage User request is in (script conversion, audio creation, others).
- What action was performed (e.g., data creation, update, or deletion).
- When the action occurred (timestamp).
- Additional context (e.g., request payload or response status).

Audit logs can be stored in a database, file, or external logging service or custom logging functions.

# Use of ORM
ALembic migration, and beanie for ORM 
# Common Response Structure
Have a common exception function with same json response
mandatorily having keys, you can add more if required.
- status
- message
- code
```python
async def get_training_data(self, user_id: str):
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing 'id'")
        return await self.service.get_training_data(user_id)
```
Use pydantic for DTO validation
```python
async def get_attempt_by_id(self, request: AttemptRequest) -> AttemptResponse:
    if not request.user_id:
        raise HTTPException(status_code=400, detail="Missing 'userId'")
    if not request.attempt_id:
        raise HTTPException(status_code=400, detail="Missing 'attemptId'")
```
# Rest Api document -> Api Get, Patch, Put, All request cant be get
# Formatter
Use balck formatter
pylance
flake8
# Questions
1. Why package-lock.json?
2. requirements.txt - some dependencies were removed why?
3. Move port and host to initiate fastAPi in Config