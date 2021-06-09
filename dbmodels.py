from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Table, Column, Integer, String, DateTime, Date, Text, BLOB, ForeignKey, JSON, BOOLEAN, Numeric
from sqlalchemy import MetaData
from sqlalchemy import select
from sqlalchemy import and_, or_
from sqlalchemy.orm import sessionmaker
from datetime import date
import sentry_sdk
import json

with open("config.json") as config_file:
    config_data = json.load(config_file)

##set the db data
dbUser = config_data["dbUser"]
dbPassword = config_data["dbPass"]
dbAddress = config_data["dbAddress"]
dbPort = config_data["dbPort"]
dbName = config_data["dbName"]


try:
    engine = create_engine(f"mysql+pymysql://{dbUser}:{dbPassword}@{dbAddress}:{dbPort}/{dbName}", pool_pre_ping=True, pool_size=10, pool_recycle=25200, max_overflow=20, echo=False)
    Base = declarative_base()
    Session = sessionmaker(bind=engine)
    session = Session()
except Exception as e:
            print(f" {e.__class__.__name__}: {e}  - Connecting to DB through an error") 
            sentry_sdk.capture_exception(e)    




class documents(Base):
    __tablename__ = 'documents'

    id = Column(String(25), primary_key=True)
    reportDefinitionId = Column(String(25), ForeignKey('templates.id'), nullable=False)
    createdAt = Column(DateTime, nullable=False)
    updatedAt = Column(DateTime, nullable=False)
    data = Column('data', Text, nullable=False)
    isTestData = Column('isTestData', BOOLEAN, nullable=False)
    pdfFile = Column('pdfFile', BLOB)
    pdfFileSize = Column('pdfFileSize', Integer)


    def __repr__(self):
        return f"documents(id={self.id!r}, reportDefinitionId={self.reportDefinitionId!r}, createdAt={self.createdAt!r}, updatedAt={self.updatedAt!r}, data{self.data!r}, isTestData={self.isTestData!r}, pdfFile = {self.pdfFile!r}, pdfFileSize = {self.pdfFileSize!r})"

class templates(Base):
    __tablename__ = 'templates'

    id = Column(String(25), primary_key=True)
    reportDefinition = Column(Text, nullable=False)
    createdAt = Column(DateTime, nullable=False)
    updatedAt = Column(DateTime, nullable=False)
    account = Column(String(25))
    name = Column(String(255))
    code = Column(String(25))
    testData = Column(Text, nullable=True)
    reportFormat = Column(String(25), nullable = False)
    
    
    def __repr__(self):
        return f"templates(id={self.id!r}, account = {self.account!r}, reportDefinition={self.reportDefinition!r}, createdAt={self.createdAt!r}, updatedAt={self.updatedAt!r})"
