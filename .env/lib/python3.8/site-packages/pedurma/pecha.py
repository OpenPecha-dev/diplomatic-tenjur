from typing import Collection, List, Optional

from pydantic import AnyHttpUrl, BaseModel


# Shared properties
class PageBase(BaseModel):
    id: str
    page_no: int
    content: str
    name: str
    vol: str
    image_link: Optional[str] = None


class Page(PageBase):
    note_ref: Optional[str]


class NotesPage(PageBase):
    pass


class Text(BaseModel):
    id: str
    pages: List[Page]
    notes: Optional[List[NotesPage]]


class PedurmaPreviewPage(BaseModel):
    content: str


class PedurmaNoteEdit(BaseModel):
    image_link: str
    image_no: int
    page_no: int
    ref_start_page_no: str
    ref_end_page_no: str
    vol: int


class EditorContent(BaseModel):
    content: str


class BaseLayer(BaseModel):
    content: str


class PechaBase(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    img: Optional[AnyHttpUrl] = None


class PechaCreate(PechaBase):
    id: str
    title: str


class PechaUpdate(PechaBase):
    id: str
    title: str


class PechaInDBBase(PechaBase):
    id: str
    title: str
    owner_id: int
    img: Optional[AnyHttpUrl] = None

    class Config:
        orm_mode = True


class Pecha(PechaInDBBase):
    pass


class PechaInDB(PechaInDBBase):
    pass
