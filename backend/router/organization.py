from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session
from crud.organization import (create_organization,get_organizations,get_organization_by_id,update_organization,delete_organization)
from core.dependencies import get_current_user,require_role, UserRole
from dependencies.database import get_db
from schemas.organization import  OrganizationCreate,OrganizationResponse,OrganizationUpdate
from models.user import User

router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"]
)


from fastapi import status

@router.post(
    "/",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED
)
def create_org(organization: OrganizationCreate,db: Session = Depends(get_db)):
    
    return create_organization(db, organization)



@router.get("/",response_model=list[OrganizationResponse])
def get_all_organizations(db: Session = Depends(get_db),current_user: User = Depends(require_role(UserRole.ADMIN))):
    
    return get_organizations(db)



@router.get( "/{organization_id}",response_model=OrganizationResponse)
def get_organization(organization_id: int, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    
    
    if current_user.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="you can not see other organization data")
    return get_organization_by_id(
        db,
        organization_id
    )
    
    
@router.put("/{organization_id}", response_model=OrganizationResponse)

def update_org(organization_id: int, organization_update: OrganizationUpdate, db: Session = Depends(get_db),current_user: User = Depends(require_role(UserRole.ADMIN))):

    return update_organization(
        db=db,
        organization_id=organization_id,
        organization_update=organization_update
    )
    
    
@router.delete("/{organization_id}")
def delete_org(organization_id: int, db: Session = Depends(get_db),current_user: User = Depends(require_role(UserRole.ADMIN))):
    
    return delete_organization(
        db=db,
        organization_id=organization_id
    )