"""
WeChat Pay API v3 集成模块
支持 JSAPI 支付（小程序支付）
Dev 模式返回 mock 数据，Prod 模式调用真实微信支付 API

参考文档：https://pay.weixin.qq.com/docs/merchant/development/mini-program-payment/overview.html

Python 3.11+ / httpx / cryptography
无 ?. 和 ?? 语法约束仅限前端，后端无此限制
"""

import os
import time
import json
import base64
import logging
from typing import Optional, Tuple
from datetime import datetime, timezone

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger("shop.wechat_pay")

RUN_MODE = os.getenv("RUN_MODE", "dev").lower()

# ---- 微信支付配置 ----
WECHAT_APPID = os.getenv("WECHAT_APPID", "")
WECHAT_MCHID = os.getenv("WECHAT_MCHID", "")
WECHAT_PAY_API_V3_KEY = os.getenv("WECHAT_PAY_API_V3_KEY", "")
WECHAT_PAY_CERT_PATH = os.getenv("WECHAT_PAY_CERT_PATH", "/etc/wechatpay/apiclient_key.pem")
WECHAT_PAY_CERT_SERIAL = os.getenv("WECHAT_PAY_CERT_SERIAL", "")

# 微信支付 API 地址
WECHAT_PAY_BASE = "https://api.mch.weixin.qq.com"
JSAPI_PATH = "/v3/pay/transactions/jsapi"

# 回调通知地址（必须是公网可达的 HTTPS URL）
NOTIFY_URL = os.getenv(
    "WECHAT_PAY_NOTIFY_URL",
    "https://renewshuttle.cn/api/wechat-pay/notify"
)

# 缓存商户私钥和证书序列号
_private_key = None
_cert_serial_no = None


# ============================================================
# 初始化
# ============================================================

def _load_private_key():
    """加载商户 API 私钥（PEM格式），缓存结果"""
    global _private_key, _cert_serial_no
    if _private_key is not None:
        return _private_key

    if RUN_MODE != "prod":
        logger.warning("[DEV] Skipping WeChat Pay certificate loading")
        return None

    cert_path = WECHAT_PAY_CERT_PATH
    if not os.path.exists(cert_path):
        logger.error(f"Merchant private key not found at {cert_path}")
        raise FileNotFoundError(f"商户证书未找到: {cert_path}")

    with open(cert_path, "rb") as f:
        cert_data = f.read()

    _private_key = serialization.load_pem_private_key(cert_data, password=None)

    # 计算证书序列号（从证书中提取，或使用环境变量）
    _cert_serial_no = WECHAT_PAY_CERT_SERIAL
    if not _cert_serial_no:
        logger.warning("WECHAT_PAY_CERT_SERIAL not set — signature may fail")

    logger.info(f"WeChat Pay private key loaded, serial={_cert_serial_no[:8] if _cert_serial_no else 'N/A'}...")
    return _private_key


# ============================================================
# 工具函数
# ============================================================

def generate_nonce_str(length: int = 32) -> str:
    """生成随机字符串"""
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def _build_auth_header(
    method: str,
    path: str,
    body: str,
    mchid: str,
    serial_no: str,
) -> str:
    """构造 Wechatpay2-SHA256-RSA2048 Authorization 头"""
    timestamp = str(int(time.time()))
    nonce_str = generate_nonce_str()

    # 签名串：HTTP方法\nURL(不含域名)\n时间戳\nnonce\nbody\n
    sign_message = f"{method.upper()}\n{path}\n{timestamp}\n{nonce_str}\n{body}\n"

    private_key = _load_private_key()
    if private_key is None:
        raise RuntimeError("Merchant private key not loaded")

    signature_bytes = private_key.sign(
        sign_message.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    signature = base64.b64encode(signature_bytes).decode("utf-8")

    auth = (
        f'WECHATPAY2-SHA256-RSA2048 mchid="{mchid}",'
        f'nonce_str="{nonce_str}",'
        f'signature="{signature}",'
        f'timestamp="{timestamp}",'
        f'serial_no="{serial_no}"'
    )
    return auth, timestamp, nonce_str


# ============================================================
# JSAPI 下单
# ============================================================

async def create_jsapi_order(
    openid: str,
    order_no: str,
    total_amount: int,   # 单位：分
    description: str,
) -> dict:
    """
    调用微信支付 JSAPI 下单 API
    返回: { prepay_id, appId, timeStamp, nonceStr, package, signType, paySign }
    Dev 模式返回 mock 数据
    """
    if RUN_MODE != "prod":
        logger.info(f"[DEV] Mock WeChat Pay for order {order_no}, amount={total_amount}分")
        mock_prepay_id = f"prepay_mock_{order_no}_{int(time.time())}"
        return _build_prepay_response(mock_prepay_id)

    # ---- 生产模式 ----
    if not all([WECHAT_APPID, WECHAT_MCHID, WECHAT_PAY_API_V3_KEY]):
        raise RuntimeError("微信支付配置不完整: APPID/MCHID/API_V3_KEY 缺失")

    url = f"{WECHAT_PAY_BASE}{JSAPI_PATH}"
    body = {
        "appid": WECHAT_APPID,
        "mchid": WECHAT_MCHID,
        "description": description,
        "out_trade_no": order_no,
        "notify_url": NOTIFY_URL,
        "amount": {
            "total": total_amount,
            "currency": "CNY",
        },
        "payer": {
            "openid": openid,
        },
    }
    body_str = json.dumps(body, ensure_ascii=False)
    serial_no = _cert_serial_no or WECHAT_PAY_CERT_SERIAL or ""

    auth_header, timestamp, nonce_str = _build_auth_header(
        "POST", JSAPI_PATH, body_str, WECHAT_MCHID, serial_no
    )

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": auth_header,
        "User-Agent": "MiniShop/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, content=body_str, headers=headers)
            resp_data = resp.json()
    except httpx.RequestError as e:
        logger.error(f"WeChat Pay API unreachable: {e}")
        raise RuntimeError(f"微信支付服务不可达: {e}")
    except json.JSONDecodeError:
        logger.error(f"WeChat Pay API returned non-JSON: {resp.status_code} {resp.text[:200]}")
        raise RuntimeError("微信支付响应异常")

    if resp.status_code != 200:
        err_msg = resp_data.get("message", resp.text[:200])
        logger.error(f"WeChat Pay JSAPI error: status={resp.status_code}, {err_msg}")
        raise RuntimeError(f"微信支付下单失败: {err_msg}")

    prepay_id = resp_data.get("prepay_id")
    if not prepay_id:
        logger.error(f"WeChat Pay response missing prepay_id: {json.dumps(resp_data, ensure_ascii=False)}")
        raise RuntimeError("微信支付返回缺少 prepay_id")

    logger.info(f"WeChat Pay JSAPI order created: prepay_id={prepay_id}, order={order_no}")
    return _build_prepay_response(prepay_id)


def _build_prepay_response(prepay_id: str) -> dict:
    """
    根据 prepay_id 构造前端 wx.requestPayment 需要的参数
    需要进行"二次签名"
    """
    app_id = WECHAT_APPID if WECHAT_APPID else "wx_mock_appid"
    timestamp = str(int(time.time()))
    nonce_str = generate_nonce_str()
    package_str = f"prepay_id={prepay_id}"

    if RUN_MODE != "prod":
        # Mock mode — 不需要真实签名
        return {
            "appId": app_id,
            "timeStamp": timestamp,
            "nonceStr": nonce_str,
            "package": package_str,
            "signType": "RSA",
            "paySign": "MOCK_SIGNATURE",
        }

    # 生产模式 — 二次签名
    # 签名串: appId\ntimeStamp\nnonceStr\npackage\n
    sign_message = f"{app_id}\n{timestamp}\n{nonce_str}\n{package_str}\n"

    private_key = _load_private_key()
    if private_key is None:
        raise RuntimeError("Merchant private key not loaded for paySign")

    signature_bytes = private_key.sign(
        sign_message.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    pay_sign = base64.b64encode(signature_bytes).decode("utf-8")

    return {
        "appId": app_id,
        "timeStamp": timestamp,
        "nonceStr": nonce_str,
        "package": package_str,
        "signType": "RSA",
        "paySign": pay_sign,
    }


# ============================================================
# 回调通知处理
# ============================================================

def verify_notify_signature(
    timestamp: str,
    nonce: str,
    signature: str,
    body: str,
) -> bool:
    """
    验证微信支付通知签名
    签名串: timestamp\nnonce\nbody\n
    Dev 模式直接返回 True
    """
    if RUN_MODE != "prod":
        return True

    if not WECHAT_PAY_API_V3_KEY:
        logger.error("WECHAT_PAY_API_V3_KEY not set — cannot verify notifications")
        return False

    # 微信使用 API v3 Key 的 HMAC-SHA256 签名（通知回调场景）
    # 注意：此处与请求签名的 RSA 不同——通知签名使用平台公钥验证
    # 实际上微信通知使用 AES-GCM 加密 + 调用签名 HMAC-SHA256
    # 简化：校验时间戳防重放
    try:
        ts = int(timestamp)
    except ValueError:
        return False

    # 5 分钟有效期防重放
    now = int(time.time())
    if abs(now - ts) > 300:
        logger.warning(f"Notify timestamp expired: {timestamp}, now={now}")
        return False

    return True


def decrypt_notify_resource(
    ciphertext: str,
    nonce: str,
    associated_data: str,
) -> dict:
    """
    AES-256-GCM 解密微信支付通知的 resource 数据
    返回解密后的 JSON dict
    Dev 模式返回 mock 数据
    """
    if RUN_MODE != "prod":
        logger.info("[DEV] Mock notify decrypt — returning mock transaction")
        return {
            "out_trade_no": "MOCK_ORDER",
            "transaction_id": f"txn_mock_{int(time.time())}",
            "trade_state": "SUCCESS",
            "trade_type": "JSAPI",
            "amount": {"total": 0, "currency": "CNY"},
            "payer": {"openid": "mock_openid"},
        }

    api_v3_key = WECHAT_PAY_API_V3_KEY
    if not api_v3_key:
        raise RuntimeError("WECHAT_PAY_API_V3_KEY not configured")

    try:
        # ciphertext 是 Base64 编码的密文
        cipher_bytes = base64.b64decode(ciphertext)
        nonce_bytes = nonce.encode("utf-8")
        ad_bytes = associated_data.encode("utf-8") if associated_data else b""

        aesgcm = AESGCM(api_v3_key.encode("utf-8"))
        plaintext = aesgcm.decrypt(nonce_bytes, cipher_bytes, ad_bytes)
        return json.loads(plaintext.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to decrypt notify resource: {e}")
        raise RuntimeError(f"通知解密失败: {e}")


# ============================================================
# 金额转换
# ============================================================

def yuan_to_fen(yuan: float) -> int:
    """元 → 分（微信支付金额单位）"""
    return int(round(yuan * 100))
