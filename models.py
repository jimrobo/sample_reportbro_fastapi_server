from datetime import datetime, date, timezone
from typing import Any, Optional, List, Union
from pydantic import BaseModel, constr, ValidationError, condecimal, Field, Json, validator, root_validator
from enum import Enum, IntEnum
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
import re
import json
import sentry_sdk
from sentry_sdk.integrations.redis import RedisIntegration
from pydantic import schema
from pydantic.fields import ModelField


class templateFormatEnum(str, Enum):
    pdf = 'pdf'
    xlsx = 'xlsx'

class createReport(BaseModel):
    account: str = Field(description = "The account the document is being requested for")
    templateId: str = Field(description = "The template ID you received when you created the template through the create template endpoint")
    templateData: dict = Field(description = "The template data to merge with the template")
    templateFormat: templateFormatEnum = Field (description = "The format required. 'pdf' or 'xlsx'")
    isTest: Optional [bool] = Field (False, description = 'True = TEST' )

class createTemplate(BaseModel):
    account: Optional[str] = Field("", description = "The account the document is being requested for")
    templateDefinition: dict = Field(description = "The template definition from the report designor")
    sampleData: Optional[dict] = Field(None, description = "sample data object to poll")
    reportFormat: templateFormatEnum = Field(description = "The format the report needs to be in ")
    name: str = Field(description = "The name of the template")
    code: str = Field(description = "The name of the template")

class getTemplates(BaseModel):
    account: str = Field(description = "the account to return templates for")

class getTemplateData(BaseModel):
      templateId: str = Field(description = "The documentId you received when you first created the report")   

class reportReprint(BaseModel):
    account: str = Field(description = "The account the document is being requested for")
    documentId: str = Field(description = "The documentId you received when you first created the report")
