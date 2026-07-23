import os
import json


class EngineConfig:
    # --- 性能预算配置 ---
    CAMERA_INDEX = 0
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 480

    # --- 自适应 EMA 去抖参数（保留作为备用/或被一欧元取代） ---
    ALPHA_MIN = 0.05        # 静止微调时的平滑度（越小越稳）
    ALPHA_MAX = 0.60        # 高速移动时的跟手度（越大越快）
    VELOCITY_THRESHOLD = 35.0  # 速度临界值（像素）

    # ── 💡 新增：P2 一欧元低通滤波器超参 ──
    ONE_EURO_MIN_CUTOFF = 1.5    # 越低在静止时越防手抖（默认 0.8）
    ONE_EURO_BETA = 0.03         # 越大在快速挥动时越无跟手延迟（默认 0.03）
    ONE_EURO_D_CUTOFF = 1.0      # 速度截止频率（固定 1.0）

    # --- 鼠标控制死区与动态锁 ---
    MOUSE_DEAD_ZONE = 3     # 低于 3 像素的生理振颤直接归零
    CLICK_LOCK_DURATION = 0.15  # 点击时锁死坐标 150 毫秒，防止指针漂移
    PINCH_THRESHOLD = 0.05
    ENGINE_ACTIVE = True  # 大拇指与食指捏合的归一化距离阈值

    # --- 滚轮灵敏度 ---
    SCROLL_SENSITIVITY = 1.8   
    SCROLL_DEAD_ZONE = 0.015   

    # --- 主题索引 ---
    CURRENT_THEME_INDEX = 0    # 0: 蓝, 1: 绿, 2: 橙
    
    # --- 舒适活动范围（重映射边界） ---
    CALIB_X_MIN = 0.25        # Comfort zone left boundary
    CALIB_X_MAX = 0.75        # Comfort zone right boundary
    CALIB_Y_MIN = 0.30        # Comfort zone top boundary
    CALIB_Y_MAX = 0.70        # Comfort zone bottom boundary

    CONFIG_FILE_PATH = "config.json"

    @classmethod
    def load_json(cls):
        if os.path.exists(cls.CONFIG_FILE_PATH):
            try:
                with open(cls.CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, val in data.items():
                        if hasattr(cls, key):
                            setattr(cls, key, val)
                print("[Config] Local config loaded successfully.")
            except Exception as e:
                print(f"[Config] Load failed, using defaults: {e}")

    @classmethod
    def save_json(cls):
        try:
            config_dict = {
                "ALPHA_MIN": cls.ALPHA_MIN,
                "ALPHA_MAX": cls.ALPHA_MAX,
                "PINCH_THRESHOLD": cls.PINCH_THRESHOLD,
                "SCROLL_SENSITIVITY": cls.SCROLL_SENSITIVITY,
                "SCROLL_DEAD_ZONE": cls.SCROLL_DEAD_ZONE,
                "CLICK_LOCK_DURATION": cls.CLICK_LOCK_DURATION,
                "VELOCITY_THRESHOLD": cls.VELOCITY_THRESHOLD,
                "CURRENT_THEME_INDEX": cls.CURRENT_THEME_INDEX,
                "ENGINE_ACTIVE": cls.ENGINE_ACTIVE,
                "CALIB_X_MIN": cls.CALIB_X_MIN,
                "CALIB_X_MAX": cls.CALIB_X_MAX,
                "CALIB_Y_MIN": cls.CALIB_Y_MIN,
                "CALIB_Y_MAX": cls.CALIB_Y_MAX,
            }
            with open(cls.CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Save failed: {e}")

    # --- 视线追踪/面部防误触配置 ---
    FACE_YAW_MIN = 0.45       
    FACE_YAW_MAX = 2.20       
    FACE_PITCH_MIN = 0.38     

    # --- 连招 DTW 配置 ---
    MACRO_WINDOW_SIZE = 35     
    DTW_THRESHOLD = 0.18