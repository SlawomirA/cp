from sqlalchemy import Column, Integer, LargeBinary

from src.database import Base, engine


class PDFFile(Base):
    __tablename__ = "pdf_files"
    id = Column(Integer, primary_key=True, index=True)
    file_data = Column(LargeBinary)


Base.metadata.create_all(bind=engine)
