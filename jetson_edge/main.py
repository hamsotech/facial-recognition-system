"""
main.py — Entry Point cho Jetson Edge Agent
═══════════════════════════════════════════════════════
Cách dùng:
  python main.py <session_id>
  python main.py <session_id> --check-gpu     # Chỉ kiểm tra GPU rồi thoát
  python main.py <session_id> --no-gpu-check  # Bỏ qua kiểm tra và chạy ngay
"""

import sys
import uuid
import argparse
import logging

# ── Cấu hình logging đẹp ra terminal ────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Jetson Edge AI — Hệ thống điểm danh khuôn mặt độc lập"
    )
    parser.add_argument(
        "session_id",
        help="UUID của phiên điểm danh (từ Spring Boot /api/sessions)"
    )
    parser.add_argument(
        "--check-gpu",
        action="store_true",
        help="Chỉ kiểm tra GPU và in thông tin, không chạy pipeline"
    )
    parser.add_argument(
        "--no-gpu-warn",
        action="store_true",
        help="Cho phép chạy trên CPU mà không cảnh báo (không khuyến nghị)"
    )
    return parser.parse_args()


def validate_session_id(session_id: str) -> bool:
    try:
        uuid.UUID(session_id.strip())
        return True
    except ValueError:
        return False


def main():
    args = parse_args()

    # ── Validate session_id ──────────────────────────────────────
    if not validate_session_id(args.session_id):
        logger.error(f"session_id không hợp lệ: '{args.session_id}'")
        logger.error("Định dạng đúng: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        sys.exit(1)

    # ── Kiểm tra GPU (luôn chạy khi khởi động) ──────────────────
    from gpu_manager import DeviceManager, print_gpu_report, get_gpu_stats

    gpu_stats = get_gpu_stats()
    print_gpu_report(gpu_stats)

    # Nếu chỉ muốn kiểm tra GPU rồi thoát
    if args.check_gpu:
        logger.info("--check-gpu: Kiểm tra xong, thoát chương trình.")
        sys.exit(0)

    # Cảnh báo nếu không có GPU
    if not gpu_stats.available and not args.no_gpu_warn:
        logger.warning("=" * 58)
        logger.warning("⚠️  CẢNH BÁO: Không phát hiện thấy GPU CUDA!")
        logger.warning("   Pipeline sẽ chạy trên CPU — có thể quá chậm cho realtime.")
        logger.warning("   Nếu Jetson của bạn có GPU, hãy kiểm tra:")
        logger.warning("   1. JetPack đã cài đúng chưa? (jetson_release)")
        logger.warning("   2. PyTorch đúng phiên bản Jetson chưa?")
        logger.warning("      https://forums.developer.nvidia.com/c/agx-autonomous-machines/jetson/")
        logger.warning("   Thêm --no-gpu-warn để bỏ qua cảnh báo này.")
        logger.warning("=" * 58)

        confirm = input("\n❓ Bạn có muốn tiếp tục trên CPU không? [y/N]: ").strip().lower()
        if confirm != "y":
            logger.info("Đã hủy. Thoát chương trình.")
            sys.exit(0)

    # ── Chạy pipeline chính ──────────────────────────────────────
    logger.info(f"[Main] Khởi động pipeline với session_id: {args.session_id}")
    from client import JetsonClient
    from pipeline import run_pipeline

    # Kiểm tra server có chạy không trước khi bắt đầu
    client = JetsonClient()
    if not client.health_check():
        logger.error("[Main] Server không phản hồi! Kiểm tra FastAPI server trên PC.")
        logger.error(f"       SERVER_URL = {__import__('config').SERVER_URL}")
        sys.exit(1)

    run_pipeline(session_id=args.session_id.strip())


if __name__ == "__main__":
    main()
