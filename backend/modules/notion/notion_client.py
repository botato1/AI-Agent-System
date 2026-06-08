from notion_client import Client

from backend.core.config import settings

# env에 저장된 NOTION_TOKEN을 사용해서 Notion Client 객체를 생성하는 함수
def get_notion_client():
    if not settings.NOTION_TOKEN:
        raise ValueError("NOTION_TOKEN이 설정되지 않았습니다.")

    return Client(auth=settings.NOTION_TOKEN)


# env에 저장된 NOTION_DATABASE_ID를 사용해서 Notion 데이터베이스에 접근 가능한지 테스트하는 함수
def test_notion_connection():

    if not settings.NOTION_DATABASE_ID:
        raise ValueError("NOTION_DATABASE_ID가 설정되지 않았습니다.")

    notion = get_notion_client()

    database = notion.databases.retrieve(
        database_id=settings.NOTION_DATABASE_ID
    )

    return {
        "status": "success",
        "database_id": settings.NOTION_DATABASE_ID,
        "title": database.get("title", [])
    }