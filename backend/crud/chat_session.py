from sqlalchemy.orm import Session

from models.chat_session import ChatSession


def create_session(db: Session,title: str,organization_id: int, user_id: int):
    
    session = ChatSession(
        title=title,
        organization_id=organization_id,
        user_id=user_id
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def get_session( db: Session,session_id: int,  organization_id: int, user_id: int):
    
    return (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.organization_id == organization_id,
            ChatSession.user_id == user_id,
        )
        .first()
    ) 

def get_user_sessions( db: Session, user_id: int):
    
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )

def delete_session(db: Session, session: ChatSession):
    
    db.delete(session)
    db.commit()