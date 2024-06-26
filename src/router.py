from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import (
    RefreshToken,
    Token,
    _get_token_from_request,
    check_authenticate,
    check_credentials,
    get_user_from_request,
)
from src.crud import (
    create_contact,
    create_personal_model,
    create_user_model,
    delete_chat,
    get_chats_by_user,
    get_messages_model,
    get_personal_model,
    get_user_model,
    update_profile_model,
    update_user_model,
)
from src.dependencies import get_async_session
from src.enums import UserRole
from src.mail import send_mail_background
from src.models import User
from src.schemas import (
    AddContact,
    ChangePassword,
    Credentials,
    MailSchema,
    RefreshTokenSchema,
    Register,
    UpdateProfile,
    UserView,
)
from src.utils import (
    get_password_hash,
    remove_private_data,
)

router = APIRouter(prefix="/user")


@router.post("/registration", status_code=status.HTTP_201_CREATED)
async def registration_user(
    db: Annotated[AsyncSession, Depends(get_async_session)], body: Register
):
    user = await create_user_model(db, body)
    personal = await create_personal_model(db, body, user["id"])
    await db.commit()
    schema = {**user, **personal}
    if "modified_date" not in schema:
        schema["modified_date"] = None
    if "password" in schema:
        del schema["password"]
    return UserView(**schema)


@router.post("/login", status_code=status.HTTP_201_CREATED)
async def create_token(
    db: Annotated[AsyncSession, Depends(get_async_session)],
    credentials: Credentials,
):
    return await check_authenticate(db, credentials)


@router.post("/refresh-token", status_code=status.HTTP_201_CREATED)
async def refresh_token(token: RefreshTokenSchema):
    return RefreshToken(token=token.token, role=UserRole.noone).create_token()


@router.put("/change/password/{user_id}", status_code=status.HTTP_200_OK)
async def change_password(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    credentials: ChangePassword,
    background_tasks: BackgroundTasks,
):
    token = _get_token_from_request(request)
    user_data = Token(token, [UserRole.user, UserRole.administrator])
    user_data.check_permission(exclude=False)
    user_id = user_data.user_id()
    user_email = user_data.user_email()
    user = await check_credentials(db, credentials)
    if user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provided credentials not correct",
        )
    new_password_to_mail = credentials.new_password
    credentials.new_password = get_password_hash(credentials.new_password)
    changed_user_credentials = await update_user_model(
        db, credentials, user_id=user_id
    )
    if "password" in changed_user_credentials:
        msg = f"Your password was changed {new_password_to_mail}"
        mail = MailSchema(
            recipients=[user_email],
            body=msg,
            subject="Ouath2: Changed password",
        )
        send_mail_background(background_tasks, mail)
        del changed_user_credentials["password"]
    return changed_user_credentials


@router.get("/profile/{user_id}", status_code=status.HTTP_200_OK)
async def profile_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    user_id: int,
):
    token = _get_token_from_request(request)
    user_data = Token(token, [UserRole.user, UserRole.administrator])
    user_data.check_permission(exclude=False)
    user_id_from_token = user_data.user_id()
    personal_model = await get_personal_model(db, user_id)
    user_model = await get_user_model(db, user_id)
    schema = {**user_model.__dict__, **personal_model}
    if user_id != user_id_from_token:
        remove_private_data(schema, to_another_user=True)
    return schema


@router.put("/change/profile", status_code=status.HTTP_200_OK)
async def change_profile(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    profile: UpdateProfile,
):
    token = _get_token_from_request(request)
    user_data = Token(token, [UserRole.user, UserRole.administrator])
    user_data.check_permission(exclude=False)
    user_id = user_data.user_id()
    profile_model = await update_profile_model(db, profile, user_id)
    user_model = await get_user_model(db, user_id)
    schema = {**profile_model, **user_model.__dict__}
    remove_private_data(schema)
    return schema


@router.post("/add-contact", status_code=status.HTTP_201_CREATED)
async def add_contact(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    payload: AddContact,
):
    token = _get_token_from_request(request)
    user_data = Token(token, [UserRole.user, UserRole.administrator])
    user_data.check_permission(exclude=False)
    user_id = user_data.user_id()
    if user_id != payload.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Permission Error"
        )
    chat = await create_contact(db, payload)
    await db.commit()
    return chat


@router.get("/contacts", status_code=status.HTTP_200_OK)
async def list_contacts(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    token = _get_token_from_request(request)
    user_data = Token(token, [UserRole.user, UserRole.administrator])
    user_data.check_permission(exclude=False)
    owner = user_data.user_id()
    return await get_chats_by_user(db, owner)


@router.delete("/contact/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    chat_id: int,
):
    token = _get_token_from_request(request)
    user_data = Token(token, [UserRole.user, UserRole.administrator])
    user_data.check_permission(exclude=False)
    await delete_chat(db, chat_id)


@router.get("/chat/{chat_id}", status_code=status.HTTP_200_OK)
async def get_chat(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    chat_id: int,
):
    token = _get_token_from_request(request)
    user_data = Token(token, [UserRole.user, UserRole.administrator])
    user_data.check_permission(exclude=False)
    return await get_messages_model(db, chat_id)


@router.get("/me")
async def me(user: Annotated[User, Depends(get_user_from_request)]):
    return user
