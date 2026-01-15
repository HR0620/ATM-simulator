# 非接触型 AI ATM アプリ構成

## 1. プロジェクト概要
本プロジェクトは、**非接触型 ATM シミュレーター** です。  
AI（コンピュータビジョン）を用いて、ユーザーが画面に触れずに操作できるインターフェースを提供します。  

また、**オブジェクト指向プログラミング（OOP）** を採用しており、  
コードの可読性・保守性・説明のしやすさを重視しています。

---

## 2. ソフトウェア構成（クラスの役割）

アプリケーションは **モジュールごとに責務を明確に分けて** 実装されています。  
この責務分離（Separation of Concerns）が設計上の大きな特徴です。

### **コアモジュール（「エンジン」）**
- **`CameraManager`** (`vision/camera_manager.py`)  
  - **役割**: Webカメラの管理  
  - **詳細**: カメラの起動、フレーム読み込み、リソース解放を安全に行います。  
    OpenCV の生の呼び出しを抽象化しています。

- **`AIModel`** (`ai/model_loader.py`)  
  - **役割**: Teachable Machine（TensorFlow/Keras）モデルをラップ  
  - **詳細**: `.h5` モデルと `labels.txt` を読み込みます。  
    画像フレームを入力として、予測と信頼度を返します。

---

### **ロジックモジュール（「脳」）**
- **`FacePositionChecker`** (`core/face_checker.py`)  
  - **役割**: Face ID の判定  
  - **詳細**: Haar Cascades を使って顔を検出します。  
    顔がガイド枠内に一定フレーム数収まっていることを確認し、  
    誤って解除されないようにします（例：30フレーム）。

- **`GestureValidator`** (`core/gesture_validator.py`)  
  - **役割**: AI の出力を安定化  
  - **詳細**: 揺れや誤検出を防ぎます。ジェスチャー（Left/Center/Right）を確定するのは以下の場合のみです：
    1. AI が `"free"`（手が画面外）を予測していない  
    2. 信頼度が高い（例：85％以上）  
    3. 同じジェスチャーが N フレーム連続で検出された  

---

### **UI & コントローラー（「顔」）**
- **`ATMController`** (`core/controller.py`)  
  - **役割**: オーケストラの指揮者  
  - **詳細**: 他のクラスを初期化し、アプリのフロー（Face Guide → ATM Screen）を管理します。  
    メインの更新ループも担当します。

- **`FaceGuideScreen` & `ATMUI`** (`ui/screens.py`)  
  - **役割**: ビジュアル表示  
  - **詳細**:  
    - `FaceGuideScreen` はカメラ映像と操作指示を表示  
    - `ATMUI` はボタン表示と選択中のアクションをハイライト

---

## 3. 実行方法

1. **依存ライブラリのインストール**  
```bash
pip install -r requirements.txt
```

2.  **AIモデルの設定**:
    -   Teachable Machineで取得した `keras_model.h5` and `labels.txt` を `model/` フォルダに入れます。
    -   `labels.txt` には `0 left`, `1 center`, `2 right`, `3 free` の4つのクラスを含める必要があります。

3.  **アプリの起動**:
    -   `main.py` をコードエディター等で開きます。
    -   F5キーを押すとアプリケーションが起動します。

## 4. 評価指標
-   **Roboustness**: `GestureValidator` ensures that the ATM doesn't react to random movements. The `free` class explicitly handles "no operation" states.
-   **Extensibility**: 新たな画面を追加するには，`ui/screens.py` に新しいクラスを作成し，`ATMController` に遷移メソッドを追加する必要があります．
