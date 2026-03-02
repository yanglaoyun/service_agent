<!-- 语音输入组件-->
<!-- src/components/VoiceInput.vue -->
<template>
  <a-button
    v-if="recording"
    shape="circle"
    variant="filled"
    danger
    @click="stopRecording"
    :loading="starting"
    class="voice-button"
  >
      <!--     录音中 -->
    <img :src="iconRecorderActive" style="width: 20px; height: 20px;" />
  </a-button>
  <!-- 点击录音 -->
  <a-button
    v-else
    shape="circle"
    variant="filled"
    color="default"
    @click="startRecording"
    :loading="starting"
    class="voice-button"
  >
    <img :src="iconRecorder" style="width: 20px; height: 20px;" />
  </a-button>
</template>

<script setup lang="ts">
import api, {getVolToken} from '../api'
import iconRecorder from '../assets/recorder.svg'
import iconRecorderActive from '../assets/recorder@active.svg'
import { ref, onUnmounted, shallowRef } from 'vue'
import { LabASR } from 'byted-ailab-speech-sdk'

// 定义事件
const emit = defineEmits<{
  (e: 'result', text: string, fullData: Record<string, any>): void
  (e: 'error', error: string): void
}>()

// 定义状态
const recordStopping = ref(false)
const fullResponseRef = ref<any>()
const recording = ref(false)
const starting = ref(false)

// 构建完整URL的函数
function buildFullUrl(url: string, auth: Record<string, string>) {
  const arr = []
  for (const key in auth) {
    arr.push(`${key}=${encodeURIComponent(auth[key])}`)
  }
  return `${url}?${arr.join('&')}`
}

// 初始化ASR客户端
const asrClient = shallowRef(
  LabASR({
    onMessage: async (text, fullData) => {
      fullResponseRef.value = fullData
      console.log('ASR识别结果:', text, fullData)
      emit('result', text, fullData)
    },
    onStart() {
      console.log('ASR录音开始')
    },
    onClose() {
      console.log('ASR连接关闭')
      recording.value = false
    },
    onError(error) {
      console.error('ASR错误:', error)
      emit('error', 'WebSocket 异常')
      stopRecording()
    },
  })
)

// 开始录音
const startRecording = async () => {
  console.log('=== 开始录音流程 ===')

  if (recording.value || starting.value) return
  starting.value = true
  recordStopping.value = false
  const appid = import.meta.env.VITE_VOLC_APPID
  const accessKey = import.meta.env.VITE_VOLC_ACCESS_KEY
  const auth: Record<string, string> = {}
  // console.log('===  开始获取火山引擎Token ===')
  // 检查环境变量

  if (!appid || !accessKey) {
    emit('error', '请配置火山引擎 AppID 和 AccessKey')
    starting.value = false
    return
  }

  console.log('配置火山引擎 AppID 和 AccessKey成功')
  try {
    console.log('===  开始获取火山引擎Token ===')
    const tokenRes = await getVolToken({appid,accessKey})
    console.log('tokenRes:', tokenRes)
    const token = tokenRes.data?.jwt_token
    console.log('火山token', token['appid'])
    if (!token) {
      emit('error', '获取 token 失败，请检查配置')
      starting.value = false
      return
    }

    console.log('=== 获取火山引擎Token 成功 ===')
    if (token) {
      // auth.api_resource_id = 
      auth.api_app_key = 
      auth.api_access_key = 
    }
    const fullUrl = buildFullUrl(
      `wss://openspeech.bytedance.com/api/v3/sauc/bigmodel`,
      auth,
    )
    const params = {
      url: fullUrl,
      config: {
        user: {
          uid: 'byted sdk demo',
        },
        audio: {
          format: 'pcm',
          rate: 16000,
          bits: 16,
          channel: 1,
        },
        request: {
          model_name: 'bigmodel',
          show_utterances: true,
        },
      },
    }

    asrClient.value.connect(params)
    starting.value = false
    recording.value = true

    await asrClient.value.startRecord()
  } catch (error: any) {
    recording.value = false
    stopRecording()

    let errorMsg = error.message || '录音启动失败'
    if (error.message?.includes('Permission denied')) {
      errorMsg = '请开启麦克风权限'
    }

    emit('error', errorMsg)
  }
}

// 停止录音
const stopRecording = () => {
  if (recordStopping.value) {
    return
  }
  recordStopping.value = true
  recording.value = false  // 立即更新UI状态
  asrClient.value.stopRecord()
}

// 组件卸载时清理
onUnmounted(() => {
  console.log('组件卸载，停止录音')
  stopRecording()
})

// 暴露方法给父组件
defineExpose({
  startRecording,
  stopRecording
})
</script>

<!-- #2d2d2d或者1e1e1e-->
<style scoped>.voice-button {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;
  background: #2d2d2d;

  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.voice-button:hover {
  background: #e0e0e0;
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.voice-button:active {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* 录音中状态的特殊样式 */
.voice-button.recording {
  background: #ff4d4f;
  position: relative;
}

.voice-button.recording:hover {
  background: #f5222d;
  box-shadow: 0 6px 12px rgba(255, 77, 79, 0.3);
}

/* 添加脉冲动画 */
.voice-button.recording::before {
  content: '';
  position: absolute;
  top: -1px;
  left: -1px;
  right: -1px;
  bottom: -1px;
  border-radius: 50%;
  background: rgba(255, 77, 79, 0.3);
  animation: pulse 1.5s ease-out infinite;
  z-index: -1;
}

@keyframes pulse {
  0% {
    transform: scale(0.8);
    opacity: 1;
  }
  100% {
    transform: scale(1.5);
    opacity: 0;
  }
}
</style>


