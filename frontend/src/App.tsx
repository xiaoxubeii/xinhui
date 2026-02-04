import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Activity, FileText, HeartPulse, LineChart, Stethoscope, Utensils } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import type { AgentId } from './components/Sidebar';
import { SearchBox } from './components/SearchBox';
import { AgentCases } from './components/AgentCases';
import { Footer } from './components/Footer';
import { ChatView } from './components/ChatView';
import { ClinicalIframeView } from './components/ClinicalIframeView';
import './App.css';

interface AgentInfo {
  id: AgentId;
  label: string;
  description: string;
  icon: ReactNode;
  tag?: string;
}

type ArtifactStatus = 'parsed' | 'raw' | 'failed';

interface UploadedArtifact {
  id: string;
  name: string;
  type: string;
  size: number;
  status: ArtifactStatus;
  parsed?: Record<string, unknown>;
  rawText?: string;
  error?: string;
}

const normalizeKey = (value: string) =>
  value.replace(/[\s_\-()（）\[\]{}]+/g, '').toLowerCase();

const getNumberFromValue = (value: unknown) => {
  if (typeof value === 'number' && !Number.isNaN(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value.replace(/[^\d.+-]/g, ''));
    if (!Number.isNaN(parsed)) {
      return parsed;
    }
  }
  return undefined;
};

const getStringFromValue = (value: unknown) => {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed ? trimmed : undefined;
  }
  if (typeof value === 'number' && !Number.isNaN(value)) {
    return String(value);
  }
  return undefined;
};

const isPlainRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const flattenRecord = (record: Record<string, unknown>) => {
  const result: Record<string, unknown> = { ...record };
  Object.values(record).forEach((value) => {
    if (!isPlainRecord(value)) {
      return;
    }
    Object.entries(value).forEach(([key, nestedValue]) => {
      if (isPlainRecord(nestedValue)) {
        Object.entries(nestedValue).forEach(([deepKey, deepValue]) => {
          result[deepKey] = deepValue;
        });
        return;
      }
      result[key] = nestedValue;
    });
  });
  return result;
};

const pickNumber = (record: Record<string, unknown>, keys: string[]) => {
  const normalizedMap = new Map<string, unknown>();
  Object.entries(record).forEach(([key, value]) => {
    normalizedMap.set(normalizeKey(key), value);
  });
  for (const key of keys) {
    const exact = record[key];
    const exactValue = getNumberFromValue(exact);
    if (exactValue !== undefined) {
      return exactValue;
    }
    const normalized = normalizedMap.get(normalizeKey(key));
    const normalizedValue = getNumberFromValue(normalized);
    if (normalizedValue !== undefined) {
      return normalizedValue;
    }
  }
  return undefined;
};

const pickString = (record: Record<string, unknown>, keys: string[]) => {
  const normalizedMap = new Map<string, unknown>();
  Object.entries(record).forEach(([key, value]) => {
    normalizedMap.set(normalizeKey(key), value);
  });
  for (const key of keys) {
    const exact = record[key];
    const exactValue = getStringFromValue(exact);
    if (exactValue) {
      return exactValue;
    }
    const normalized = normalizedMap.get(normalizeKey(key));
    const normalizedValue = getStringFromValue(normalized);
    if (normalizedValue) {
      return normalizedValue;
    }
  }
  return undefined;
};

const pickSex = (record: Record<string, unknown>) => {
  const raw = pickString(record, ['sex', 'gender', '性别']);
  if (!raw) {
    return undefined;
  }
  const normalized = raw.toLowerCase();
  if (normalized.includes('male') || normalized.includes('man') || normalized.includes('男') || normalized === 'm' || normalized === '1') {
    return 'male';
  }
  if (normalized.includes('female') || normalized.includes('woman') || normalized.includes('女') || normalized === 'f' || normalized === '0') {
    return 'female';
  }
  return undefined;
};
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface Session {
  id: string;
  title: string;
  agentId: AgentId | null;
  messages: Message[];
  artifacts: UploadedArtifact[];
  pendingCount: number;
  pdfSuggestion: 'report' | 'prescription' | null;
  createdAt: string;
}

interface PdfDefaults {
  payload: {
    patient: {
      name: string;
      patient_id: string;
      age: number;
      sex: 'male' | 'female';
      height_cm: number;
      weight_kg: number;
      diagnosis: string[];
      has_hypertension: boolean;
      has_diabetes: boolean;
      has_pacemaker: boolean;
      has_orthopedic_issues: boolean;
    };
    cpet_results: {
      vo2_peak: number;
      hr_max: number;
      hr_rest: number;
      max_workload: number;
      max_mets: number;
      vt1_vo2: number | null;
      vt1_hr: number | null;
      vt1_workload: number | null;
      vt2_vo2: number | null;
      vt2_hr: number | null;
      vt2_workload: number | null;
      ischemia_hr: number | null;
      arrhythmia_hr: number | null;
    };
    exercise_test: {
      max_mets: number | null;
      has_complex_arrhythmia: boolean;
      has_angina: boolean;
      has_dyspnea: boolean;
      has_dizziness: boolean;
      symptom_onset_mets: number | null;
      st_depression_mm: number;
      has_abnormal_hr_response: boolean;
      has_abnormal_bp_response: boolean;
    };
    non_exercise_test: {
      lvef: number | null;
      has_cardiac_arrest_history: boolean;
      has_chf: boolean;
      has_ischemia_symptoms: boolean;
      has_resting_arrhythmia: boolean;
      has_clinical_depression: boolean;
    };
    has_cardiac_surgery: boolean;
    has_balance_issues: boolean;
    has_fall_history: boolean;
    physician_name: string | null;
  };
  missing: string[];
}

const createId = () => `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;

const parseValue = (value: string) => {
  const trimmed = value.trim();
  if (!trimmed) {
    return '';
  }
  const numeric = Number(trimmed);
  if (!Number.isNaN(numeric)) {
    return numeric;
  }
  return trimmed;
};

const detectDelimiter = (line: string) => {
  const candidates = [',', '\t', ';'];
  let best = ',';
  let bestCount = -1;
  for (const char of candidates) {
    const count = line.split(char).length - 1;
    if (count > bestCount) {
      bestCount = count;
      best = char;
    }
  }
  return best;
};

const parseCsvToObject = (text: string) => {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length === 0) {
    return null;
  }
  const delimiter = detectDelimiter(lines[0]);
  const rows = lines.map((line) => line.split(delimiter).map((cell) => cell.trim()));
  if (rows.length < 2) {
    return null;
  }
  const header = rows[0];
  const headerKey = header.join(',').toLowerCase();
  const keyLike = header.length === 2 && (headerKey.includes('key') || headerKey.includes('指标') || headerKey.includes('项目'));
  if (keyLike) {
    const result: Record<string, unknown> = {};
    rows.slice(1).forEach((row) => {
      const key = row[0]?.trim();
      if (!key) {
        return;
      }
      result[key] = parseValue(row[1] ?? '');
    });
    return result;
  }
  const firstRow = rows[1];
  const result: Record<string, unknown> = {};
  header.forEach((key, index) => {
    if (!key) {
      return;
    }
    result[key] = parseValue(firstRow?.[index] ?? '');
  });
  return result;
};

const parseResultsFile = async (file: File): Promise<UploadedArtifact> => {
  const name = file.name;
  const type = file.type || 'application/octet-stream';
  const size = file.size;
  const artifactBase = {
    id: createId(),
    name,
    type,
    size,
    status: 'raw' as ArtifactStatus,
  };

  try {
    if (name.endsWith('.json') || type.includes('json')) {
      const text = await file.text();
      const parsed = JSON.parse(text);
      return {
        ...artifactBase,
        status: 'parsed',
        parsed: typeof parsed === 'object' && parsed !== null ? (parsed as Record<string, unknown>) : { data: parsed },
        rawText: text.slice(0, 4000),
      };
    }
    if (name.endsWith('.csv') || type.includes('csv') || name.endsWith('.txt') || type.includes('text')) {
      const text = await file.text();
      const parsed = parseCsvToObject(text);
      if (parsed) {
        return {
          ...artifactBase,
          status: 'parsed',
          parsed,
          rawText: text.slice(0, 4000),
        };
      }
      return {
        ...artifactBase,
        status: 'raw',
        rawText: text.slice(0, 4000),
      };
    }
    return {
      ...artifactBase,
      status: 'raw',
    };
  } catch (error) {
    return {
      ...artifactBase,
      status: 'failed',
      error: error instanceof Error ? error.message : '解析失败',
    };
  }
};

const collectParsedResults = (artifacts: UploadedArtifact[]) =>
  artifacts
    .filter((item) => item.status === 'parsed' && item.parsed && isPlainRecord(item.parsed))
    .reduce<Record<string, unknown>>((acc, item) => {
      const flattened = flattenRecord(item.parsed as Record<string, unknown>);
      return { ...acc, ...flattened };
    }, {});

const buildContext = (agentId: AgentId | null, artifacts: UploadedArtifact[]) => {
  const parsedResults = collectParsedResults(artifacts);
  const files = artifacts.map((item) => ({
    name: item.name,
    type: item.type,
    size: item.size,
    status: item.status,
    error: item.error,
  }));
  const rawTexts = artifacts
    .filter((item) => item.rawText && item.status !== 'failed')
    .map((item) => ({
      name: item.name,
      text: item.rawText,
    }));
  return {
    agent_id: agentId,
    cpet_results: parsedResults,
    files,
    raw_texts: rawTexts,
    output_format: 'markdown',
  };
};

const getPdfDefaults = (artifacts: UploadedArtifact[]): PdfDefaults | null => {
  const parsed = collectParsedResults(artifacts);
  if (Object.keys(parsed).length === 0) {
    return null;
  }

  const name = pickString(parsed, ['name', 'patient_name', '姓名', '病人姓名']);
  const patientId = pickString(parsed, ['patient_id', 'patientid', '病历号', '住院号', '编号', 'id']);
  const age = pickNumber(parsed, ['age', '年龄']);
  const sex = pickSex(parsed);
  const height = pickNumber(parsed, ['height', 'height_cm', '身高', '身高cm']);
  const weight = pickNumber(parsed, ['weight', 'weight_kg', '体重']);

  const vo2Peak = pickNumber(parsed, ['vo2_peak', 'vo2peak', 'vo2 peak', 'VO2peak', 'VO2 Peak']);
  const hrMax = pickNumber(parsed, ['hr_max', 'hrmax', 'HRmax', 'max_hr']);
  const hrRest = pickNumber(parsed, ['hr_rest', 'hrrest', 'rest_hr', 'HRrest']);
  const maxWorkload = pickNumber(parsed, ['max_workload', 'max workload', 'max_load', 'workload_max', '最大功率']);
  const maxMets = pickNumber(parsed, ['max_mets', 'max mets', 'mets_max', '最大METS']);

  const vt1Vo2 = pickNumber(parsed, ['vt1_vo2', 'vt1vo2', 'vt1 vo2', 'AT VO2', 'AT_VO2']);
  const vt1Hr = pickNumber(parsed, ['vt1_hr', 'vt1hr', 'AT HR', 'AT_HR']);
  const vt1Workload = pickNumber(parsed, ['vt1_workload', 'vt1 load', 'AT_workload']);
  const vt2Vo2 = pickNumber(parsed, ['vt2_vo2', 'vt2vo2']);
  const vt2Hr = pickNumber(parsed, ['vt2_hr', 'vt2hr']);
  const vt2Workload = pickNumber(parsed, ['vt2_workload', 'vt2 load']);
  const ischemiaHr = pickNumber(parsed, ['ischemia_hr', 'ischemia hr']);
  const arrhythmiaHr = pickNumber(parsed, ['arrhythmia_hr', 'arrhythmia hr']);

  const missing: string[] = [];
  if (!name) missing.push('姓名');
  if (!patientId) missing.push('病历号');
  if (!age || age <= 0) missing.push('年龄');
  if (!sex) missing.push('性别');
  if (!height || height <= 0) missing.push('身高');
  if (!weight || weight <= 0) missing.push('体重');
  if (!vo2Peak || vo2Peak <= 0) missing.push('VO2peak');
  if (!hrMax || hrMax <= 0) missing.push('HR max');
  if (!hrRest || hrRest <= 0) missing.push('HR rest');
  if (!maxWorkload || maxWorkload <= 0) missing.push('最大功率');
  if (!maxMets || maxMets <= 0) missing.push('最大 METS');

  const defaults = {
    name: '未提供',
    patientId: `AUTO-${Date.now().toString(36)}`,
    age: 50,
    sex: 'male' as const,
    height: 170,
    weight: 70,
    vo2Peak: 20,
    hrMax: 150,
    hrRest: 70,
    maxWorkload: 100,
    maxMets: 6,
  };

  return {
    payload: {
      patient: {
        name: name ?? defaults.name,
        patient_id: patientId ?? defaults.patientId,
        age: age && age > 0 ? age : defaults.age,
        sex: sex ?? defaults.sex,
        height_cm: height && height > 0 ? height : defaults.height,
        weight_kg: weight && weight > 0 ? weight : defaults.weight,
        diagnosis: [],
        has_hypertension: false,
        has_diabetes: false,
        has_pacemaker: false,
        has_orthopedic_issues: false,
      },
      cpet_results: {
        vo2_peak: vo2Peak && vo2Peak > 0 ? vo2Peak : defaults.vo2Peak,
        hr_max: hrMax && hrMax > 0 ? hrMax : defaults.hrMax,
        hr_rest: hrRest && hrRest > 0 ? hrRest : defaults.hrRest,
        max_workload: maxWorkload && maxWorkload > 0 ? maxWorkload : defaults.maxWorkload,
        max_mets: maxMets && maxMets > 0 ? maxMets : defaults.maxMets,
        vt1_vo2: vt1Vo2 ?? null,
        vt1_hr: vt1Hr ?? null,
        vt1_workload: vt1Workload ?? null,
        vt2_vo2: vt2Vo2 ?? null,
        vt2_hr: vt2Hr ?? null,
        vt2_workload: vt2Workload ?? null,
        ischemia_hr: ischemiaHr ?? null,
        arrhythmia_hr: arrhythmiaHr ?? null,
      },
      exercise_test: {
        max_mets: maxMets && maxMets > 0 ? maxMets : defaults.maxMets,
        has_complex_arrhythmia: false,
        has_angina: false,
        has_dyspnea: false,
        has_dizziness: false,
        symptom_onset_mets: null,
        st_depression_mm: 0,
        has_abnormal_hr_response: false,
        has_abnormal_bp_response: false,
      },
      non_exercise_test: {
        lvef: null,
        has_cardiac_arrest_history: false,
        has_chf: false,
        has_ischemia_symptoms: false,
        has_resting_arrhythmia: false,
        has_clinical_depression: false,
      },
      has_cardiac_surgery: false,
      has_balance_issues: false,
      has_fall_history: false,
      physician_name: null,
    },
    missing,
  };
};

const getPlaceholder = (agentId: AgentId | null) => {
  switch (agentId) {
    case 'analysis':
      return '上传 CPET 或手表数据，开始运动数据分析…';
    case 'prescription':
      return '上传 CPET 报告或结果，提出处方需求…';
    case 'health':
      return '上传 CPET 结果，询问运动风险评估…';
    case 'diet':
      return '上传 CPET 结果或报告，询问营养与食疗建议…';
    case 'report':
      return '上传 CPET 报告或结果，提出解读问题…';
    default:
      return '上传 CPET 报告或输入问题…';
  }
};

function App() {
  const agents: AgentInfo[] = useMemo(
    () => [
      {
        id: 'analysis',
        label: '运动数据分析',
        description: '上传 CPET 或手表数据，生成运动指标分析与趋势摘要。',
        icon: <LineChart className="w-4 h-4" />,
      },
      {
        id: 'report',
        label: 'CPET 报告解析',
        description: '上传 CPET 报告，生成结构化解析与关键指标摘要。',
        icon: <FileText className="w-4 h-4" />,
      },
      {
        id: 'prescription',
        label: '个体化运动处方',
        description: '基于 CPET 指标生成个体化运动处方与随访建议。',
        icon: <HeartPulse className="w-4 h-4" />,
      },
      {
        id: 'health',
        label: '运动风险评估',
        description: '评估运动风险分层并给出运动管理建议。',
        icon: <Activity className="w-4 h-4" />,
      },
      {
        id: 'diet',
        label: '营养与食疗建议',
        description: '结合风险分层给出营养与食疗方向建议。',
        icon: <Utensils className="w-4 h-4" />,
      },
      {
        id: 'clinical',
        label: '临床智能体',
        description: '面向临床问题的智能问答与决策辅助。',
        icon: <Stethoscope className="w-4 h-4" />,
        tag: 'Alpha',
      },
    ],
    []
  );

  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<AgentId | null>(null);
  const [mode, setMode] = useState<'search' | 'chat' | 'clinical'>('search');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? null,
    [activeSessionId, sessions]
  );

  const activeAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) ?? null,
    [agents, selectedAgentId]
  );

  const ensureSession = (agentId: AgentId | null) => {
    const newSession: Session = {
      id: createId(),
      title: '新会话',
      agentId,
      messages: [],
      artifacts: [],
      pendingCount: 0,
      pdfSuggestion: null,
      createdAt: new Date().toLocaleString(),
    };
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
    return newSession;
  };

  const updateSession = (sessionId: string, updater: (session: Session) => Session) => {
    setSessions((prev) => prev.map((session) => (session.id === sessionId ? updater(session) : session)));
  };

  const handleNewSession = () => {
    ensureSession(selectedAgentId);
    setMode(selectedAgentId === 'clinical' ? 'clinical' : 'search');
  };

  const handleSelectAgent = (agentId: AgentId) => {
    setSelectedAgentId(agentId);
    setActiveSessionId(null);
    setMode(agentId === 'clinical' ? 'clinical' : 'search');
  };

  const handleSelectSession = (sessionId: string) => {
    const session = sessions.find((item) => item.id === sessionId);
    if (session) {
      setSelectedAgentId(session.agentId);
    }
    setActiveSessionId(sessionId);
    setMode(session?.agentId === 'clinical' ? 'clinical' : 'chat');
  };


  const appendMessage = (sessionId: string, message: Message) => {
    updateSession(sessionId, (session) => {
      const nextMessages = [...session.messages, message];
      const shouldUpdateTitle = session.messages.length === 0 && message.role === 'user';
      return {
        ...session,
        title: shouldUpdateTitle ? message.content.slice(0, 16) : session.title,
        messages: nextMessages,
      };
    });
  };

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) {
      return;
    }
    const session = activeSession ?? ensureSession(selectedAgentId);
    const parsedArtifacts = await Promise.all(Array.from(files).map(parseResultsFile));
    const nextArtifacts = [...session.artifacts, ...parsedArtifacts];
    updateSession(session.id, (current) => ({
      ...current,
      artifacts: nextArtifacts,
    }));
    const nextAgentId = session.agentId ?? selectedAgentId;
    if (nextAgentId === 'report' || nextAgentId === 'prescription' || nextAgentId === 'analysis') {
      setMode('chat');
      void runAutoAnalysis(session.id, nextAgentId, nextArtifacts);
    }
  };

  const adjustPending = (sessionId: string, delta: number) => {
    updateSession(sessionId, (session) => ({
      ...session,
      pendingCount: Math.max(0, session.pendingCount + delta),
    }));
  };

  const sendMessage = async (content: string) => {
    const session = activeSession ?? ensureSession(selectedAgentId);
    const history = session.messages.slice(-6).map((msg) => ({
      role: msg.role,
      content: msg.content,
    }));
    const userMessage: Message = {
      id: createId(),
      role: 'user',
      content,
      timestamp: new Date().toLocaleTimeString(),
    };
    appendMessage(session.id, userMessage);
    adjustPending(session.id, 1);
    setMode('chat');

    const context = buildContext(session.agentId ?? selectedAgentId, session.artifacts);
    const apiBase = import.meta.env.VITE_API_BASE ?? '';
    try {
      const response = await fetch(`${apiBase}/api/agent/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: content,
          context,
          history,
        }),
      });
      if (!response.ok) {
        throw new Error(`API ${response.status}`);
      }
      const data = await response.json();
      const assistantMessage: Message = {
        id: createId(),
        role: 'assistant',
        content: data?.answer || '暂无可用回答。',
        timestamp: new Date().toLocaleTimeString(),
      };
      appendMessage(session.id, assistantMessage);
    } catch (error) {
      const assistantMessage: Message = {
        id: createId(),
        role: 'assistant',
        content: `调用失败：${error instanceof Error ? error.message : '未知错误'}`,
        timestamp: new Date().toLocaleTimeString(),
      };
      appendMessage(session.id, assistantMessage);
    } finally {
      adjustPending(session.id, -1);
    }
  };

  const runAutoAnalysis = async (
    sessionId: string,
    agentId: AgentId | null,
    artifacts: UploadedArtifact[]
  ) => {
    if (agentId !== 'report' && agentId !== 'prescription' && agentId !== 'analysis') {
      return;
    }
    const parsedResults = collectParsedResults(artifacts);
    if (Object.keys(parsedResults).length === 0) {
      return;
    }
    const question =
      agentId === 'prescription'
        ? '请基于上传的 CPET 结果生成个体化运动处方的核心要点（要点化、分层清晰）。'
        : agentId === 'analysis'
          ? '请对上传的 CPET/手表数据进行运动数据分析，输出关键指标、趋势摘要与风险提示，并给出可执行建议。'
          : '请基于上传的 CPET 结果生成结构化解析报告（包含关键指标、风险提示与临床建议）。';
    const context = buildContext(agentId, artifacts);
    const history: { role: string; content: string }[] = [];
    const apiBase = import.meta.env.VITE_API_BASE ?? '';
    adjustPending(sessionId, 1);
    try {
      const response = await fetch(`${apiBase}/api/agent/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question,
          context,
          history,
        }),
      });
      if (!response.ok) {
        throw new Error(`API ${response.status}`);
      }
      const data = await response.json();
      const assistantMessage: Message = {
        id: createId(),
        role: 'assistant',
        content: data?.answer || '暂无可用回答。',
        timestamp: new Date().toLocaleTimeString(),
      };
      appendMessage(sessionId, assistantMessage);
      updateSession(sessionId, (session) => ({
        ...session,
        pdfSuggestion: agentId === 'prescription' ? 'prescription' : 'report',
      }));
      const pdfDefaults = getPdfDefaults(artifacts);
      if (pdfDefaults && pdfDefaults.missing.length > 0) {
        const missingLabel = pdfDefaults.missing.join('、');
        appendMessage(sessionId, {
          id: createId(),
          role: 'assistant',
          content: `解析已完成。以下字段缺失将自动使用默认值：${missingLabel}。是否生成 PDF？可点击下方“生成 PDF”。`,
          timestamp: new Date().toLocaleTimeString(),
        });
      } else {
        appendMessage(sessionId, {
          id: createId(),
          role: 'assistant',
          content: '解析已完成。是否生成 PDF 报告？可点击下方“生成 PDF”。',
          timestamp: new Date().toLocaleTimeString(),
        });
      }
    } catch (error) {
      appendMessage(sessionId, {
        id: createId(),
        role: 'assistant',
        content: `自动解析失败：${error instanceof Error ? error.message : '未知错误'}`,
        timestamp: new Date().toLocaleTimeString(),
      });
    } finally {
      adjustPending(sessionId, -1);
    }
  };

  const handleSearchSubmit = (content: string) => {
    void sendMessage(content);
  };

  const handleSendMessage = (content: string) => {
    void sendMessage(content);
  };


  const pdfDefaults = useMemo(
    () => getPdfDefaults(activeSession?.artifacts ?? []),
    [activeSession?.artifacts]
  );

  return (
    <div className="min-h-screen bg-white flex">
      {/* Sidebar */}
      <Sidebar
        agents={agents}
        selectedAgentId={selectedAgentId}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectAgent={handleSelectAgent}
        onNewSession={handleNewSession}
        onSelectSession={handleSelectSession}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((prev) => !prev)}
      />

      {/* Main Content */}
      <main
        className={`flex-1 min-h-screen flex flex-col ${sidebarCollapsed ? 'ml-[72px]' : 'ml-[240px]'}`}
      >
        {mode === 'search' ? (
          <>
            <div className="flex-1 flex flex-col items-center justify-center px-6 py-10">
              {/* Logo */}
              <motion.h1
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
                className="text-5xl font-bold text-black tracking-tight"
              >
                心衡智问
              </motion.h1>
              <p className="text-sm text-gray-500 mt-2 mb-8">
                临床运动评估与健康平台
              </p>

              {/* Search Box */}
              <SearchBox
                agentLabel={activeAgent?.label ?? null}
                agentTag={activeAgent?.tag ?? null}
                placeholder={getPlaceholder(activeAgent?.id ?? null)}
                onSubmit={handleSearchSubmit}
                onUpload={handleUpload}
                uploadedFiles={activeSession?.artifacts ?? []}
              />

              {activeAgent && (
                <div className="mt-4 text-xs text-gray-500 flex items-center gap-2">
                  <span className="px-2 py-1 rounded-full bg-gray-100 text-gray-600">
                    Agent | {activeAgent.label}
                  </span>
                  {activeAgent.tag && (
                    <span className="px-2 py-1 rounded-full bg-gray-200 text-gray-700 text-[10px]">
                      {activeAgent.tag}
                    </span>
                  )}
                  <span className="text-gray-400">{activeAgent.description}</span>
                </div>
              )}

              {/* Agent Cases */}
              <AgentCases />
            </div>

            {/* Footer */}
            <Footer />
          </>
        ) : mode === 'clinical' ? (
          <ClinicalIframeView />
        ) : (
          <ChatView
            messages={activeSession?.messages ?? []}
            agentId={activeAgent?.id ?? null}
            agentLabel={activeAgent?.label ?? null}
            agentTag={activeAgent?.tag ?? null}
            placeholder={getPlaceholder(activeAgent?.id ?? null)}
            pdfDefaults={pdfDefaults}
            pdfSuggestion={activeSession?.pdfSuggestion ?? null}
            onDismissPdfSuggestion={() => {
              if (activeSession) {
                updateSession(activeSession.id, (session) => ({
                  ...session,
                  pdfSuggestion: null,
                }));
              }
            }}
            uploadedFiles={activeSession?.artifacts ?? []}
            onUpload={handleUpload}
            isThinking={(activeSession?.pendingCount ?? 0) > 0}
            sessionTitle={activeSession?.title}
            onSend={handleSendMessage}
          />
        )}
      </main>
    </div>
  );
}

export default App;
