<script setup>
import { onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

function onKeydown(e) {
  if (e.key === 'Escape') emit('close')
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) window.addEventListener('keydown', onKeydown)
    else window.removeEventListener('keydown', onKeydown)
  },
)

onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div v-if="open" class="backdrop" @click.self="emit('close')">
    <div class="panel-box" role="dialog" aria-label="Help">
      <div class="panel-head">
        <h2>Help — NAE Observatory 사용 안내</h2>
        <button class="close" @click="emit('close')" aria-label="close">×</button>
      </div>

      <div class="panel-body">
        <p class="intro">
          NAE Observatory는 <strong>관찰 전용(read-only) Dashboard</strong>입니다.
          여기 표시되는 모든 값은 실제 production 파일/프로세스를 읽어온 것이며,
          이 화면에서 어떤 조작을 하더라도 production 작업 자체는 시작·중지·재시작되지 않습니다.
        </p>

        <section>
          <h3>Production</h3>
          <dl>
            <dt>Current Job</dt>
            <dd>지금 대시보드가 관찰 중인 작업 대상입니다. 실행 중인 TSU 프로세스의 <code>--identifier</code> 값을 그대로 읽어옵니다.</dd>

            <dt>Source / Volume</dt>
            <dd>현재 처리 중인 원본 문서(예: ANDREW FULLER — VOLUME 01)를 사람이 읽기 쉬운 이름으로 표시한 것입니다.</dd>

            <dt>Processed</dt>
            <dd>지금까지 실제로 평가된 candidate(claim 후보 문장) 수입니다. 추정치가 아니라 <code>tsu_report.json</code>의 <code>candidates_evaluated</code> 값 그대로입니다.</dd>

            <dt>Total</dt>
            <dd>이 volume에서 평가해야 할 전체 candidate 수입니다.</dd>

            <dt>Progress %</dt>
            <dd>Processed ÷ Total을 그대로 계산한 값입니다.</dd>

            <dt>Throughput (처리량)</dt>
            <dd>지금까지의 누적 처리 속도를 시간당 candidate 수로 환산한 값입니다.</dd>

            <dt>ETA</dt>
            <dd><strong>확정된 완료 시각이 아니라, 현재 처리 속도가 그대로 유지된다는 가정 아래 계산한 예상치</strong>입니다. 처리 속도가 바뀌면 ETA도 함께 바뀝니다.</dd>

            <dt>Errors</dt>
            <dd>LLM claim 추출 과정에서 관찰된 오류 건수입니다. 0이 정상이며, 개별 candidate 실패는 자동으로 건너뛰고 계속 진행됩니다.</dd>

            <dt>Process Status (C1)</dt>
            <dd>TSU 추출 프로세스가 실제로 살아있는지(<code>ps aux</code> 확인) 여부입니다. Dashboard는 이 프로세스를 시작하거나 멈추지 않고 관찰만 합니다.</dd>
          </dl>
        </section>

        <section>
          <h3>Pipeline</h3>
          <dl>
            <dt>Registration</dt>
            <dd>원본 문서가 NAE 저장소에 정식 등록되고 무결성 검증을 통과했는지 여부입니다. COMPLETE는 등록 완료를 뜻하며, TSU 추출 완료를 뜻하지 않습니다.</dd>

            <dt>Quality / OCR</dt>
            <dd>원문 스캔본의 OCR 품질 검사 단계입니다. Registration 과정의 일부로 처리되며, 아직 별도의 실시간 지표로는 노출되지 않습니다.</dd>

            <dt>TSU Extraction <span class="gloss">(Theological Statement Unit / 신학적 주장 단위)</span></dt>
            <dd>원문에서 신학적 주장(claim)을 LLM으로 추출하는 단계입니다. 지금 Dashboard가 실시간으로 관찰하는 핵심 작업입니다.</dd>

            <dt>Review (검토)</dt>
            <dd>추출된 TSU를 사람이 검토하는 단계입니다. 검토 전 상태는 <code>generated</code>, 검토가 끝나면 <code>reviewed</code>/<code>verified</code>/<code>rejected</code>로 바뀝니다. Dashboard는 이 상태 분포만 집계해 보여주며, 검토 자체를 수행하지 않습니다.</dd>

            <dt>Promotion (승격)</dt>
            <dd>검토를 통과(<code>verified</code>)한 TSU가 다음 단계(Embedding)로 넘어갈 자격을 얻는 것입니다. review_status가 <code>verified</code>가 되는 것이 곧 Promotion 자격 획득입니다.</dd>

            <dt>Embedding</dt>
            <dd>승격된(verified) TSU를 벡터로 변환하는 단계입니다. verified 레코드가 0건이면 구조적으로 아직 시작될 수 없습니다.</dd>

            <dt>Qdrant <span class="gloss">(Vector Database / 검색용 벡터 저장소)</span></dt>
            <dd>임베딩된 TSU가 최종적으로 저장되어 검색 가능해지는 단계입니다.</dd>

            <dt>Retrieval Validation</dt>
            <dd>저장된 TSU가 실제 검색(RAG)에서 올바르게 동작하는지 확인하는 단계입니다. 아직 이 Dashboard가 실시간으로 관찰하는 지표는 아닙니다.</dd>

            <dt>Queue</dt>
            <dd>각 volume(Fuller Vol.01~08)이 파이프라인의 어느 단계에 있는지 보여줍니다. RUNNING/QUEUED/COMPLETE/BLOCKED/ERROR로 표시하며, 실제로 실행된 적 없는 단계는 항상 QUEUED로 표시합니다(추측하지 않습니다).</dd>
          </dl>
        </section>

        <section>
          <h3>System</h3>
          <dl>
            <dt>GPU Utilization</dt>
            <dd>
              현재 GPU 사용률입니다. <strong>99%처럼 높은 값 자체는 오류가 아닙니다</strong> —
              지금 LLM이 활발하게 추론(inference)하고 있다는 뜻입니다. 온도·throttle·프로세스
              상태 등 다른 지표와 함께 봐야 실제 이상 여부를 판단할 수 있습니다.
            </dd>

            <dt>GPU Memory (VRAM)</dt>
            <dd>GPU가 사용 중인 메모리량입니다. Apple Silicon은 GPU 전용 메모리가 따로 없고 시스템 메모리(unified memory)를 공유합니다.</dd>

            <dt>CPU Utilization</dt>
            <dd>시스템 전체 CPU 사용률입니다.</dd>

            <dt>System Memory</dt>
            <dd>시스템 전체 RAM 사용량입니다.</dd>

            <dt>Disk</dt>
            <dd>디스크 사용량과 읽기/쓰기 속도입니다.</dd>

            <dt>Network</dt>
            <dd>네트워크 송수신 속도입니다.</dd>

            <dt>GPU Health / Telemetry</dt>
            <dd>
              HEALTHY/WARNING/ERROR/UNKNOWN으로 표시됩니다. <strong>GPU 사용률만으로
              판정하지 않으며</strong>, macOS가 기록한 열 경고(thermal warning) 신호만을
              근거로 판단합니다. 온도(°C)·전력(W)·클럭(MHz)·성능 상태는 sudo 권한 없이는
              읽을 수 없어 항상 UNKNOWN으로 표시됩니다. XID 오류는 NVIDIA GPU 전용 개념이라
              Apple Silicon에는 해당 사항이 없어 N/A로 표시됩니다.
            </dd>

            <dt>llama-server</dt>
            <dd>Ollama가 내부적으로 구동하는 실제 추론 엔진 프로세스입니다. ONLINE/OFFLINE 상태만 관찰합니다.</dd>

            <dt>-np / parallelism (동시 처리 슬롯 수)</dt>
            <dd>llama-server가 동시에 처리할 수 있는 요청 수입니다. 실행 중인 프로세스의 커맨드라인에서 직접 읽은 값이며, Dashboard는 이 값을 바꾸지 않습니다.</dd>

            <dt>n8n Health</dt>
            <dd>기존 n8n 자동화 서버(별도 포트)가 응답하는지 여부입니다. NAE TSU 추출과는 별개의 시스템입니다.</dd>
          </dl>
        </section>

        <section>
          <h3>Monitoring</h3>
          <dl>
            <dt>LIVE MONITOR</dt>
            <dd>LIVE는 정상 polling 중, RECONNECTING은 일시적 통신 실패, PAUSED는 사용자가 직접 OFF로 전환한 상태입니다.</dd>

            <dt>Refresh interval</dt>
            <dd>화면이 값을 다시 읽어오는 주기입니다(5/10/30/60초 중 선택, 기본값 5초).</dd>

            <dt>Last update</dt>
            <dd>가장 최근에 성공적으로 값을 읽어온 시각입니다.</dd>

            <dt>Next update</dt>
            <dd>다음 갱신이 예정된 시각입니다(현재 refresh interval 기준 예상치).</dd>

            <dt>Monitoring ON/OFF</dt>
            <dd>이 화면 자체의 polling(새로고침)만 켜고 끕니다. 아래 "Production 안전성"을 참고하세요.</dd>
          </dl>
        </section>

        <section class="safety">
          <h3>Production 안전성</h3>
          <ul>
            <li>NAE Observatory는 관찰 전용(read-only) Dashboard입니다.</li>
            <li>Monitoring ON/OFF 또는 Refresh 설정 변경은 Production 작업을 시작·중지·재시작하지 않습니다.</li>
            <li>Monitoring OFF는 이 화면의 polling만 멈추며, C1(TSU 추출)·Ollama·llama-server 등 다른 Production 프로세스에는 어떠한 영향도 주지 않습니다.</li>
            <li>이 Dashboard에는 Stop/Restart/Kill/Requeue/Model switch/Qdrant mutation 등 어떤 제어 기능도 없습니다 — API 자체에 그런 경로가 존재하지 않습니다.</li>
            <li>Help 창을 열고 닫는 것도 순수 화면 동작이며 monitoring 상태나 production에 영향을 주지 않습니다.</li>
          </ul>
        </section>

        <section>
          <h3>용어 모음</h3>
          <dl class="glossary">
            <dt>TSU</dt>
            <dd>Theological Statement Unit / 신학적 주장 단위</dd>
            <dt>Throughput</dt>
            <dd>처리량 / 시간당 처리된 candidate 수</dd>
            <dt>Promotion</dt>
            <dd>승격 / 검토 gate를 통과해 다음 pipeline으로 이동하는 상태</dd>
            <dt>Qdrant</dt>
            <dd>Vector Database / 검색용 벡터 저장소</dd>
            <dt>candidate</dt>
            <dd>후보 문장 / TSU로 추출될 수 있는 원문 문장 단위</dd>
            <dt>review_status</dt>
            <dd>검토 상태 / generated → reviewed → verified 또는 rejected</dd>
            <dt>Bottleneck</dt>
            <dd>병목 / 현재 가장 많이 사용 중인 자원(GPU/CPU/RAM)</dd>
            <dt>checkpoint</dt>
            <dd>체크포인트 / 진행 상황을 파일에 저장하는 시점(약 100건마다)</dd>
          </dl>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 5vh 16px;
  z-index: 100;
}

.panel-box {
  background: var(--panel);
  border: 1px solid var(--panel-border);
  width: 100%;
  max-width: 640px;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--panel-border);
  flex-shrink: 0;
}

.panel-head h2 {
  margin: 0;
  font-size: 13px;
  letter-spacing: 0.04em;
}

.close {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  padding: 0 4px;
}

.close:hover {
  color: var(--text);
}

.panel-body {
  overflow-y: auto;
  padding: 16px 18px 24px;
  font-size: 12px;
  line-height: 1.6;
}

.intro {
  margin: 0 0 18px;
  color: var(--text-dim);
}

.intro strong {
  color: var(--accent);
}

section {
  margin-bottom: 20px;
}

section h3 {
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--accent);
  margin: 0 0 10px;
  border-bottom: 1px solid var(--panel-border);
  padding-bottom: 6px;
}

dl {
  margin: 0;
}

dt {
  color: var(--text);
  font-weight: 600;
  margin-top: 10px;
}

dt:first-child {
  margin-top: 0;
}

dd {
  margin: 3px 0 0;
  color: var(--text-dim);
}

code {
  font-family: var(--font-mono);
  background: #0a0d0b;
  border: 1px solid var(--panel-border);
  padding: 0 4px;
  font-size: 11px;
}

.gloss {
  font-weight: 400;
  color: var(--text-dim);
  font-size: 11px;
}

.safety ul {
  margin: 0;
  padding-left: 18px;
  color: var(--text-dim);
}

.safety li {
  margin-bottom: 6px;
}

.glossary dt {
  display: inline;
  margin-top: 8px;
}

.glossary dd {
  display: block;
  margin: 0 0 4px;
}
</style>
