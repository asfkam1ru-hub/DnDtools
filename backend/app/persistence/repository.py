from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.character import Character
from app.persistence.models import CharacterRecord


class CharacterRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def create(self, character: Character) -> Character:
        with self._session_factory() as session:
            record = CharacterRecord(
                id=str(character.id),
                name=character.name,
                race=character.race,
                class_name=character.class_name,
                level=character.level,
                max_hp=character.max_hp,
                hp=character.hp,
                inventory=character.inventory,
                skills=character.skills,
                strength=character.strength,
                dexterity=character.dexterity,
                constitution=character.constitution,
                intelligence=character.intelligence,
                wisdom=character.wisdom,
                charisma=character.charisma,
            )
            session.add(record)
            session.commit()
        return character

    def list(self) -> list[Character]:
        with self._session_factory() as session:
            records = session.scalars(select(CharacterRecord)).all()
        return [self._to_domain(record) for record in records]

    def get(self, character_id: UUID) -> Character | None:
        with self._session_factory() as session:
            record = session.get(CharacterRecord, str(character_id))
        if record is None:
            return None
        return self._to_domain(record)

    def update(self, character: Character) -> Character | None:
        with self._session_factory() as session:
            record = session.get(CharacterRecord, str(character.id))
            if record is None:
                return None

            record.name = character.name
            record.race = character.race
            record.class_name = character.class_name
            record.level = character.level
            record.max_hp = character.max_hp
            record.hp = character.hp
            record.inventory = character.inventory
            record.skills = character.skills
            record.strength = character.strength
            record.dexterity = character.dexterity
            record.constitution = character.constitution
            record.intelligence = character.intelligence
            record.wisdom = character.wisdom
            record.charisma = character.charisma

            session.commit()
        return character

    def delete(self, character_id: UUID) -> bool:
        with self._session_factory() as session:
            record = session.get(CharacterRecord, str(character_id))
            if record is None:
                return False
            session.delete(record)
            session.commit()
        return True

    @staticmethod
    def _to_domain(record: CharacterRecord) -> Character:
        return Character(
            id=UUID(record.id),
            name=record.name,
            race=record.race,
            class_name=record.class_name,
            level=record.level,
            max_hp=record.max_hp,
            hp=record.hp,
            inventory=record.inventory or [],
            skills=record.skills or [],
            strength=record.strength,
            dexterity=record.dexterity,
            constitution=record.constitution,
            intelligence=record.intelligence,
            wisdom=record.wisdom,
            charisma=record.charisma,
        )
