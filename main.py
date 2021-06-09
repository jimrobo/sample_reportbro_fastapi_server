from logging import error
import json
import os
import uvicorn
from fastapi import Security, Depends, FastAPI, HTTPException
from fastapi.security.api_key import APIKeyQuery, APIKeyCookie, APIKeyHeader, APIKey
from fastapi import FastAPI, Request
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_ENTITY
from logzero import logger, logfile
import cuid
import sentry_sdk
from sentry_sdk.integrations.redis import RedisIntegration
import logzero
from logzero import setup_logger
from dbmodels import *
from reportbro import Report, ReportBroError
from models import *
import base64


with open("config.json") as config_file:
    config_data = json.load(config_file)

sentryKey = config_data['sentryKey']    
sentry_sdk.init(sentryKey, traces_sample_rate=1.0)

logfile(config_data["log"], maxBytes=10e6, backupCount=6)    # start the logging
logger.info("Program started")      # Log messages

#load the api keys
apikeyName = config_data['apikeyName']

##set the api key variables
API_KEY_NAME = "appID"
api_key_query = APIKeyQuery(name=API_KEY_NAME, auto_error=False)
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


#set up the function to protect the endpoints with the api key
async def get_api_key(
    api_key_query: str = Security(api_key_query),
    api_key_header: str = Security(api_key_header),
):
    if api_key_query in apikeyName:
        return api_key_query
    elif api_key_header in apikeyName:
        return api_key_header
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Incorrect API Key"
        )

# Test endpoint description for the docs + any other
tags_metadata = [
    {
        "name": "Test",
        "description": "A test GET endpoint for apikey testing. It simply returns {'Hello': 'account code'} to verify your api key is correct. No params are required",
    }
]        

##test report for the test endpoint
jsonString = '{"docElements":[{"elementType":"text","id":190,"containerId":"0_content","x":90,"y":80,"width":200,"height":30,"content":"This is a test report","eval":false,"styleId":"","bold":false,"italic":false,"underline":false,"strikethrough":false,"horizontalAlignment":"left","verticalAlignment":"top","textColor":"#000000","backgroundColor":"","font":"helvetica","fontSize":12,"lineSpacing":1,"borderColor":"#000000","borderWidth":1,"borderAll":false,"borderLeft":false,"borderTop":false,"borderRight":false,"borderBottom":false,"paddingLeft":2,"paddingTop":2,"paddingRight":2,"paddingBottom":2,"printIf":"","removeEmptyElement":false,"alwaysPrintOnSamePage":true,"pattern":"","link":"","cs_condition":"","cs_styleId":"","cs_bold":false,"cs_italic":false,"cs_underline":false,"cs_strikethrough":false,"cs_horizontalAlignment":"left","cs_verticalAlignment":"top","cs_textColor":"#000000","cs_backgroundColor":"","cs_font":"helvetica","cs_fontSize":12,"cs_lineSpacing":1,"cs_borderColor":"#000000","cs_borderWidth":"1","cs_borderAll":false,"cs_borderLeft":false,"cs_borderTop":false,"cs_borderRight":false,"cs_borderBottom":false,"cs_paddingLeft":2,"cs_paddingTop":2,"cs_paddingRight":2,"cs_paddingBottom":2,"spreadsheet_hide":false,"spreadsheet_column":"","spreadsheet_colspan":"","spreadsheet_addEmptyRow":false,"spreadsheet_textWrap":false}],"parameters":[{"id":1,"name":"page_count","type":"number","arrayItemType":"string","eval":false,"nullable":false,"pattern":"","expression":"","showOnlyNameType":true,"testData":""},{"id":2,"name":"page_number","type":"number","arrayItemType":"string","eval":false,"nullable":false,"pattern":"","expression":"","showOnlyNameType":true,"testData":""}],"styles":[],"version":3,"documentProperties":{"pageFormat":"A4","pageWidth":"300","pageHeight":"300","unit":"mm","orientation":"portrait","contentHeight":"","marginLeft":"","marginTop":"","marginRight":"","marginBottom":"","header":false,"headerSize":"180","headerDisplay":"always","footer":false,"footerSize":"150","footerDisplay":"always","patternLocale":"en","patternCurrencySymbol":"$"}}'
report_definition = json.loads(jsonString)

api = FastAPI(
    title='project X docsServer',
    description='<p>Project X docs server</p>',
    version='1.1',
    openapi_tags=tags_metadata,
    docs_url=None, redoc_url="/developerdocs"   
)

@api.get("/test", tags=["Test"])
async def testapikey(request: Request, api_key: APIKey = Depends(get_api_key)):
    user = apikeyName[request.headers['appID']]
    report = Report(report_definition, data=dict())
    reportFile = report.generate_pdf()
    bas64Report = base64.b64encode(reportFile)
    print(type(reportFile))
    entryResponse = {
        "Hello": user,
        "documentSampleBase64": bas64Report
    }
    logger.info(f"succesfully tested docsserver connection with user - {user} - /test")

    return entryResponse

@api.post("/reportcreate")
async def Generate(request: Request, item: createReport, api_key: APIKey = Depends(get_api_key)):
    user = apikeyName[request.headers['appID']]
    try:
        account = item.account
        templateId = item.templateId
        templateData = item.templateData
        templateFormat = item.templateFormat
        isTest = item.isTest

        ##we need to go and get the template data from the db
        search = Session()
        templateSearch =  search.query(documents, templates).join(templates).filter(documents.reportDefinitionId == templateId) 
        noOfRecords = templateSearch.count()
        if noOfRecords != 1:
            raise HTTPException(status_code=404, detail="Template ID not found")
        else:
            templateAccount = templateSearch[0].templates.account
            templateFormatData = templateSearch[0].templates.reportDefinition    

            ##if theres no account on the template set the account test to true as it is a global template
            if not templateAccount:
                accountTest = True
            else:    
                ##if there is an account set test if the account can use the template
                accountTest = templateAccount == account

            if not accountTest:
                    raise HTTPException(status_code=403, detail="Your account does match the account this template belongs too")

            else:

                ##ok...generate the report -- note is test data true puts a watermark on
                report = Report(templateFormatData, templateData, isTest)

                if templateFormat == "pdf":
                    reportFile = report.generate_pdf()
                else:
                    reportFile = report.generate_xslx()    

                ##add the data into the db as a new document
                documentId = cuid.cuid()
                datedNow = datetime.datetime.now()
                newEntry = documents(id = documentId, reportDefinitionId = templateId, createdAt = datedNow, updatedAt = datedNow, data = templateData, isTestData = isTest, reportFormat = templateFormat )
                search.add(newEntry)
                search.commit()
                search.close()

                ##now return the document back 

                base64Report = base64.b64encode(reportFile)

                responseObject = {
                    "status": "success",
                    "documentId": documentId,
                    "bas64Document": base64Report
                }

                logger.info(f"/reportcreate - new document created - ID - {documentId}, for {accountTest}")

    except Exception as e:
        logger.warning(f" {e.__class__.__name__}: {e}  - the docs creation endpoint threw an error")          
        logger.exception(e)
        sentry_sdk.capture_exception(e)
        responseObject = {
            "status": "Could not process request"
        }

    return responseObject

@api.post("/reportreprint")
async def ReGenerate(request: Request, item: reportReprint, api_key: APIKey = Depends(get_api_key)):
    user = apikeyName[request.headers['appID']]
    try:
        account = item.account
        documentId = item.documentId

        ##go and get the data from the db for the document
        docSearch = Session()
        docIdSearch = docSearch.query(documents, templates).join(templates).filter(documents.id == documentId)
        records = docIdSearch.count()
        if records != 1:
            raise HTTPException(status_code=404, detail="Document ID not found")
        else:
            dbAccount = docIdSearch[0].templates.account
            templateDefinition = docIdSearch[0].templates.reportDefinitionId
            templateData = docIdSearch[0].documents.data
            isTestData = docIdSearch[0].documents.isTestData
            reportFormat = dbAccount = docIdSearch[0].templates.reportFormat

            accounttest = account == dbAccount
            if not accountTest:
                raise HTTPException(status_code=403, detail="Your account does match the account that created this document")
            else:
                
                
                report = Report(templateDefinition, templateData, isTest)

                if reportFormat == "pdf":
                    reportFile = report.generate_pdf()
                else:
                    reportFile = report.generate_xslx() 

                    base64Report = base64.b64encode(reportFile)

                    responseObject = {
                    "status": "success",
                    "documentId": documentId,
                    "base64Document": base64Report
                }
                    docSearch.close()

    
                logger.info(f"/reportreprint - reprinted {documentId}")
        
    except Exception as e:
        logger.warning(f" {e.__class__.__name__}: {e}  - the docs re print endpoint threw an error")          
        logger.exception(e)
        sentry_sdk.capture_exception(e)
        ##if it errors raise a 422 and return the error code
        raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=e)
        

    return entryResponse    

@api.post("/addtemplate")
async def addTemplate(request: Request, item: createTemplate, api_key: APIKey = Depends(get_api_key)):
    user = apikeyName[request.headers['appID']]
    try:
        account = item.account
        templateDefinition = item.templateDefinition
        sampleData = item.sampleData
        reportFormat = item.reportFormat
        name = item.name
        code = item.code

        dbsession = Session()
        datedNow = datetime.datetime.now()
        templateId = cuid.cuid()
        newTemplate = templates(id = templateId, reportDefinition = templateDefinition, createdAt = datedNow, updatedAt = datedNow, account = account, reportFormat = reportFormat, testData = sampleData, name = name, code = code )
        dbsession.add(newTemplate)
        dbsession.commit()
        dbsession.close()
        response = {
            "status": "success",
            "templateId": templateId
        }

    
        logger.info("/addtemplate - new template from the portal")
        
    except Exception as e:
        logger.warning(f" {e.__class__.__name__}: {e}  - the add template endpoint threw an error")          
        logger.exception(e)
        sentry_sdk.capture_exception(e)
        ##if it errors raise a 422 and return the error code
        raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=e)

    return entryResponse    

@api.post("/gettemplates")
async def getAllUserTemplates(request: Request, item: getTemplates, api_key: APIKey = Depends(get_api_key)):
    user = apikeyName[request.headers['appID']]
    try:
        account = item.account
        tempSearch = Session()
        tempIdSearch = tempSearch.query(templates).filter(templates.account == account)
        records = tempIdSearch.count()
        if records == 0:
            raise HTTPException(status_code=404, detail="No Templates found for this account")
        else:
            templatesList = []
            for x in tempIdSearch:
                indTempObj = {
                    "templateName": x.name,
                    "templateCode": x.code,
                    "reportFormat": x.reportFormat,
                    "reportDefinition": x.reportDefinitionId,
                    "testData": x.testData

                }
                templatesList.append(indTempObj)

            responseObject = {
                "status": "success",
                templates: templatesList
            }    

            
        
            logger.info(f"/gettemplates - templates list requested for {account}")
        
    except Exception as e:
        logger.warning(f" {e.__class__.__name__}: {e}  - the get templates endpoint threw an error")          
        logger.exception(e)
        sentry_sdk.capture_exception(e)
        ##if it errors raise a 422 and return the error code
        raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=e)

    return entryResponse    

@api.post("/gettemplatedata")
async def getTemplateIndividual(request: Request, item: getTemplateData, api_key: APIKey = Depends(get_api_key)):
    user = apikeyName[request.headers['appID']]
    try:
        documentId = item.templateId
        tempSearch = Session()
        tempIdSearch = tempSearch.query(templates).filter(templates.id == documentId)
        records = tempIdSearch.count()
        if records != 1:
            raise HTTPException(status_code=404, detail="Template ID not found")
        else:
            templateData = tempIdSearch[0].testData
            templateName = tempIdSearch[0].name
            templateCode = tempIdSearch[0].code


            responseObject = {
                "status": "success",
                "templateName": templateName,
                "templateCode": templateCode,
                "testData": templateData
            }
            tempSearch.close()

    
            logger.info("new template from the portal")
        
    except Exception as e:
        logger.warning(f" {e.__class__.__name__}: {e}  - the get template Data endpoint threw an error")          
        logger.exception(e)
        sentry_sdk.capture_exception(e)
        ##if it errors raise a 422 and return the error code
        raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=e)

    return responseObject        


gunicornPort = config_data["gunicornPort"]
if __name__ == "__main__":
    uvicorn.run("main:api", host="127.0.0.1", port=gunicornPort,
                log_level="info", reload=True, workers=10)    
