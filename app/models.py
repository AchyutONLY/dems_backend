from sqlalchemy import Column, Integer, String, DateTime, ForeignKey,Text
from app.database import Base
from sqlalchemy.sql.expression import func
from sqlalchemy.sql.sqltypes import TIMESTAMP



class AuditLog(Base):
    __tablename__ = "auditlog"

    LogID = Column(Integer, primary_key=True)
    Timestamp = Column(TIMESTAMP(timezone=True),nullable=False,server_default=func.now())
    UserID = Column(Integer, ForeignKey("users.UserID", ondelete="SET NULL"), nullable=True)
    EventType = Column(String,nullable=False)
    Details = Column(Text,nullable=True)
    

class Case(Base):
    __tablename__ = "cases"

    CaseID = Column(Integer, primary_key=True)
    Title = Column(String, nullable=False)
    Type = Column(String, nullable=False)
    Status = Column(String, nullable=False)
    DateOpened = Column(TIMESTAMP,nullable=False,server_default=func.now())
    DateClosed = Column(TIMESTAMP,nullable=True)
    Description = Column(Text, nullable=True)
    ActingInspectorID = Column(Integer,nullable=False)


class CustodyRecords(Base):
    __tablename__ = "custodyrecords"

    RecordID = Column(Integer, primary_key=True)
    EvidenceID = Column(Integer, ForeignKey("evidenceitems.EvidenceID",ondelete="SET NULL"),nullable=True)
    Timestamp = Column(TIMESTAMP(timezone=True),nullable=False,server_default=func.now())
    ActingOfficerID = Column(Integer, ForeignKey("users.UserID",ondelete="SET NULL"),nullable=True)
    Notes = Column(String,nullable=True)


class EvidenceItems(Base):
    __tablename__ = "evidenceitems"

    EvidenceID = Column(Integer, primary_key=True)
    CaseID = Column(Integer, ForeignKey("cases.CaseID",ondelete="SET NULL"),nullable=True)
    Description = Column(String,nullable=True)
    EvidenceType = Column(String,nullable=False)
    SourceOrigin = Column(String,nullable=False)
    DateCollected = Column(TIMESTAMP(timezone=True),nullable=False,server_default=func.now())
    SubmittingOfficerID = Column(Integer,ForeignKey("users.UserID", ondelete="SET NULL"),nullable=True)

    FilePath = Column(String, nullable=True)

class User(Base):
    __tablename__="users"
    UserID=Column(Integer,primary_key=True,index=True)
    Name=Column(String,nullable=False)
    Role=Column(String,nullable=False,default="officer")
    BadgeNumber=Column(String,nullable=False,unique=True)
    Contact=Column(String,)
    Status=Column(String,default="ACTIVE")
    LastLogin=Column(TIMESTAMP(timezone=True))
    Password=Column(String,nullable=False)
    Email = Column(String,nullable=False)


class CaseAssignment(Base):
    __tablename__ = "case_assignments"

    id = Column(Integer, primary_key=True)
    CaseID = Column(Integer, ForeignKey("cases.CaseID", ondelete="CASCADE"))
    AssignedOfficerId = Column(Integer, ForeignKey("users.UserID", ondelete="CASCADE"))