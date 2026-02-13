"""
账号相关 API 路由
包含账号 CRUD、登录管理
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.account import Account
from app.models.log import SystemLog
from app.schemas.account import (
    AccountCreateRequest,
    AccountUpdateRequest,
    CookieLoginRequest,
    AccountResponse,
    AccountListResponse,
    QRCodeLoginResponse,
    LoginCheckResponse,
)
from app.core.zhihu_auth import zhihu_auth
from app.automation.browser_manager import browser_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accounts", tags=["账号管理"])


@router.get("", response_model=AccountListResponse, summary="获取账号列表")
async def list_accounts(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取所有知乎账号列表"""
    # 总数
    count_stmt = select(func.count(Account.id))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 分页查询
    offset = (page - 1) * page_size
    stmt = (
        select(Account)
        .order_by(Account.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    accounts = result.scalars().all()

    return AccountListResponse(total=total, items=accounts)


@router.get("/{account_id}", response_model=AccountResponse, summary="获取账号详情")
async def get_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 获取账号详情"""
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return account


@router.post("", response_model=AccountResponse, summary="创建账号")
async def create_account(
    request: AccountCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """创建新的知乎账号"""
    # 使用时间戳 + 短 UUID 后缀确保 profile 目录名唯一
    profile_suffix = uuid.uuid4().hex[:8]
    profile_name = f"profile_{datetime.now().strftime('%Y%m%d%H%M%S')}_{profile_suffix}"

    account = Account(
        nickname=request.nickname,
        zhihu_uid=request.zhihu_uid or "",
        cookie_data=request.cookie_data or "",
        browser_profile=profile_name,
        is_active=True,
        login_status="logged_out",
        daily_limit=request.daily_limit or 5,
        # created_at 使用模型默认值 _utcnow
    )
    db.add(account)

    # 如果提供了 Cookie，尝试 Cookie 登录
    if request.cookie_data:
        try:
            result = await zhihu_auth.cookie_login(
                account.browser_profile, request.cookie_data
            )
            if result["success"]:
                account.login_status = "logged_in"
        except Exception as e:
            logger.warning(f"Cookie 登录尝试失败: {e}")

    await db.commit()
    await db.refresh(account)

    logger.info(f"创建账号: id={account.id}, nickname={account.nickname}")
    return account


@router.put("/{account_id}", response_model=AccountResponse, summary="更新账号")
async def update_account(
    account_id: int,
    request: AccountUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """更新账号信息"""
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(account, field, value)

    await db.commit()
    await db.refresh(account)

    logger.info(f"更新账号: id={account.id}")
    return account


@router.delete("/{account_id}", summary="删除账号")
async def delete_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除账号"""
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    # 关闭该账号对应的浏览器上下文（如果存在）
    if account.browser_profile:
        try:
            await browser_manager.close_context(account.browser_profile)
        except Exception as e:
            logger.warning(f"关闭浏览器上下文失败: {e}")

    await db.delete(account)
    await db.commit()

    logger.info(f"删除账号: id={account_id}")
    return {"message": "账号已删除", "id": account_id}


@router.post(
    "/{account_id}/check-login",
    response_model=LoginCheckResponse,
    summary="检查登录态",
)
async def check_login(
    account_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    检查知乎账号的登录状态
    会打开浏览器验证 Cookie / Session 是否有效
    """
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    profile_name = account.browser_profile or f"account_{account.id}"

    try:
        result = await zhihu_auth.check_login(profile_name)

        # 更新登录状态
        if result["is_logged_in"]:
            account.login_status = "logged_in"
            if result.get("nickname"):
                account.nickname = result["nickname"]
        else:
            account.login_status = "expired"

        await db.commit()
        await db.refresh(account)

        return LoginCheckResponse(
            is_logged_in=result["is_logged_in"],
            nickname=result.get("nickname"),
            message=result["message"],
        )

    except Exception as e:
        logger.error(f"检查登录态失败: {e}")
        raise HTTPException(status_code=500, detail=f"检查失败: {str(e)}")


@router.post(
    "/{account_id}/qrcode-login",
    response_model=QRCodeLoginResponse,
    summary="扫码登录",
)
async def qrcode_login(
    account_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取知乎扫码登录二维码
    返回 base64 编码的二维码图片
    """
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    profile_name = account.browser_profile or f"account_{account.id}"

    try:
        result = await zhihu_auth.qrcode_login(profile_name, account_id=account_id)

        if result["success"]:
            # 记录日志
            log = SystemLog(
                event_type="login",
                level="info",
                message=f"请求扫码登录: {account.nickname}",
                details={"account_id": account.id},
            )
            db.add(log)
            await db.commit()

            return QRCodeLoginResponse(
                qrcode_base64=result["qrcode_base64"],
                message=result["message"],
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "获取二维码失败"),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"扫码登录失败: {e}")
        raise HTTPException(status_code=500, detail=f"扫码登录失败: {str(e)}")


@router.post(
    "/{account_id}/cookie-login",
    response_model=LoginCheckResponse,
    summary="Cookie 导入登录",
)
async def cookie_login(
    account_id: int,
    request: CookieLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    通过导入 Cookie 登录知乎
    支持 JSON 数组格式、JSON 对象格式或分号分隔格式
    """
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    profile_name = account.browser_profile or f"account_{account.id}"

    try:
        result = await zhihu_auth.cookie_login(profile_name, request.cookie_data)

        if result["success"]:
            account.login_status = "logged_in"
            account.cookie_data = request.cookie_data

            # cookie_login 内部已调用 check_login 验证，
            # 再查一次获取昵称
            check_result = await zhihu_auth.check_login(profile_name)
            if check_result.get("nickname"):
                account.nickname = check_result["nickname"]

            await db.commit()
            await db.refresh(account)

            return LoginCheckResponse(
                is_logged_in=True,
                nickname=account.nickname,
                message="Cookie 登录成功",
            )
        else:
            account.login_status = "expired"
            await db.commit()

            return LoginCheckResponse(
                is_logged_in=False,
                nickname=None,
                message=result.get("message", "Cookie 无效"),
            )

    except Exception as e:
        logger.error(f"Cookie 登录失败: {e}")
        raise HTTPException(status_code=500, detail=f"Cookie 登录失败: {str(e)}")
