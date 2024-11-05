from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base, engine




class File_Model(Base):
    __tablename__ = "File"

    FI_ID = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="Id liku")
    Name = Column(String(200), nullable=True, comment="Nazwa pliku")
    Content = Column(Text, nullable=True, comment="Zawartość tekstowa pliku")
    Corretted_Content = Column(Text, nullable=True, comment="Poprawiona przez program zawartość tekstu")
    Url = Column(String(300), nullable=True, comment="Url do pliku")

    messages = relationship("LLM_Message", back_populates="file")
    keywords = relationship("File_Keyword", back_populates="file")



class File_Keyword(Base):
    __tablename__ = "File_Keyword"

    FK_ID = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="ID pliku-keywordów")
    FI_ID = Column(Integer, ForeignKey("File.FI_ID"), nullable=False)
    Keyword = Column(String(60), nullable=True, comment="Keyword")

    file = relationship("File_Model", back_populates="keywords")


class LLM_Message(Base):
    __tablename__ = "LLM_Message"

    LLM_ID = Column(Integer, primary_key=True, autoincrement=True, comment="PK wiadomości")
    Prompt = Column(Text, nullable=True, comment="Prompt wysłany do bota")
    Answer = Column(Text, nullable=True, comment="Odpowiedź bota")
    FI_ID = Column(Integer, ForeignKey("File.FI_ID"), nullable=True, comment="Odnośnik do pliku z bazy")

    file = relationship("File_Model", back_populates="messages")


Base.metadata.create_all(bind=engine)
