from dataclasses import dataclass
import datetime
import logging
from typing import Any

from bson import ObjectId
from pymongo.database import Database
from pymongo.results import InsertOneResult, UpdateResult

from config import MongoDBSettings
from .base_mongo_db_crud_service import BaseMongoDbCrudService, DocumentStatusType
from ..db.mongo_db import get_mongo_db
from ..repository.mongo_db_repository import MongoDbRepository


@dataclass
class StaffStableDocStructure:
    """Класс структуры данных строевой записки постоянного состава."""

    date: datetime.date
    departments: dict[str, Any]
    status: DocumentStatusType

    def __dict__(self):
        return dict(
            date=self.date.isoformat(),
            departments=self.departments,
            status=self.status.value,
        )


@dataclass
class StaffStableDepartmentDocStructure:
    """
    Класс структуры данных о подразделениях постоянного состава.

    Attributes
    ----------
    id: str
        id подразделения в Апекс-ВУЗ
    name: str
        Название подразделения
    type: str
        Тип подразделения
    total: int
        Общее количество людей
    absence: dict
        Информация об отсутствии
    user: str
        Имя пользователя системы
    updated: str
        Дата обновления
    """

    id: str
    name: str
    type: str
    total: int
    absence: dict
    user: str
    updated: str


@dataclass
class StaffStableCRUDService(BaseMongoDbCrudService):
    """Класс для CRUD операций модели StaffStable"""

    def change_status(
        self, _id: str | ObjectId, status: DocumentStatusType
    ) -> UpdateResult:
        """Меняет статус документа."""
        if isinstance(_id, str):
            _id = ObjectId(_id)
        return self.update(
            {"_id": _id},
            {"$set": {"status": status}},
        )

    def make_blank_document(self, document_date: datetime.date) -> InsertOneResult:
        """Создает пустой документ с заданной датой."""
        document = StaffStableDocStructure(
            date=document_date,
            departments=dict(),
            status=DocumentStatusType.IN_PROGRESS,
        )
        result_info = self.create(document.__dict__())
        logging.info(
            f"Создан документ - строевая записка постоянного состава "
            f"за {document_date.isoformat()}. {result_info}"
        )
        return result_info


def get_staff_stable_document_service(
    mongo_db: Database = get_mongo_db(),
    collection_name: str = MongoDBSettings.STAFF_STABLE_COLLECTION,
) -> StaffStableCRUDService:
    return StaffStableCRUDService(
        repository=MongoDbRepository(mongo_db, collection_name)
    )
