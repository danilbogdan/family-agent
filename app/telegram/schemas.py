from pydantic import BaseModel, ConfigDict, Field


class TelegramUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    first_name: str = ""
    last_name: str = ""
    username: str = ""


class TelegramChat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    type: str


class TelegramVoice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    file_id: str
    duration: int = 0


class TelegramSticker(BaseModel):
    model_config = ConfigDict(extra="ignore")

    file_id: str
    file_unique_id: str
    set_name: str = ""
    emoji: str = ""


class TelegramMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message_id: int
    from_user: TelegramUser | None = Field(default=None, alias="from")
    chat: TelegramChat
    text: str = ""
    voice: TelegramVoice | None = None
    sticker: TelegramSticker | None = None
    reply_to_message: "TelegramMessage | None" = None


class TelegramCallbackQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    from_user: TelegramUser | None = Field(default=None, alias="from")
    message: TelegramMessage | None = None
    data: str = ""


class TelegramWebhook(BaseModel):
    model_config = ConfigDict(extra="ignore")

    update_id: int
    message: TelegramMessage | None = None
    callback_query: TelegramCallbackQuery | None = None
