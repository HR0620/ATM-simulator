import cv2
import time

print("=== カメラ診断ツール ===")
print("OpenCV Version:", cv2.__version__)


def test_camera(index):
    print(f"\n--- カメラ試行 (ID={index}) ---")
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print(f"ID={index}: 開けませんでした。")
        return False

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print(f"ID={index}: 接続成功。ウィンドウを確認してください。")
    print("  'SPACE' キー: このカメラでOK（確定）")
    print("  'n' キー    : 次のカメラを試す")
    print("  'q' キー    : 終了")

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"ID={index}: フレーム取得失敗")
            break

        cv2.imshow(f'Camera ID {index}', frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord(' '):
            cap.release()
            cv2.destroyAllWindows()
            return True  # OK
        elif key == ord('n'):
            break
        elif key == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            exit()

    cap.release()
    cv2.destroyAllWindows()
    return False


print("=== カメラ診断ツール (複数ID対応版) ===")
print("Windows Hello対応機の場合、ID=0が赤外線カメラ(真っ暗)で、ID=1が普通のカメラの場合があります。")

if test_camera(0):
    print("\n>>> ID=0 が正常です。設定は変更不要です。")
elif test_camera(1):
    print("\n>>> ID=1 が正常なようです！")
    print("config/atm_config.yml の device_id を 1 に変更してください。")
else:
    print("\n有効なカメラが見つかりませんでした。")
