from langgraph.graph.message import add_messages
from enum import Enum
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, SystemMessage

class InspectionCategory(str, Enum):
    FOOD_STORAGE = "Food Storage"
    KITCHEN_CLEANLINESS = "Kitchen Cleanliness"
    FOOD_HANDLER_HYGIENE = "Food Handler Hygiene"
    EQUIPMENT_CLEANLINESS = "Equipment Cleanliness"


class ConversationState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

class InspectionState(TypedDict):
    image_path: str
    mime_type: str
    category: InspectionCategory
    analysis: str
    formatted_analysis: str
    image_b64: str
