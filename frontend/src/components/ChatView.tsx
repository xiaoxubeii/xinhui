import { useEffect, useMemo, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowUp,
  Bot,
  ChevronDown,
  ClipboardList,
  FileText,
  FileUp,
  Plus,
  Square,
  Utensils,
  Watch,
  X,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { AgentId } from '@/components/Sidebar';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface PlanDraft {
  id: string;
  planType: 'exercise' | 'nutrition';
  summary: string;
  payload: Record<string, unknown>;
  warnings: string[];
  status: 'draft' | 'confirmed';
}

interface ChatViewProps {
  messages: ChatMessage[];
  agentId?: AgentId | null;
  agentLabel?: string | null;
  agentTag?: string | null;
  sessionTitle?: string;
  placeholder?: string;
  onSend: (content: string) => void;
  onUpload?: (files: FileList | null) => void;
  onRemoveUpload?: (id: string) => void;
  onStop?: () => void;
  uploadedFiles?: { id: string; name: string; status: string }[];
  isThinking?: boolean;
  streamingContent?: string;
  errorMessage?: string | null;
  onClearError?: () => void;
  pdfSuggestion?: 'report' | 'prescription' | null;
  pdfDefaults?: {
    payload: Record<string, unknown>;
    missing: string[];
  } | null;
  onDismissPdfSuggestion?: () => void;
  planDrafts?: PlanDraft[];
  onConfirmPlan?: (draftId: string) => void;
}

export function ChatView({
  messages,
  agentId,
  agentLabel,
  agentTag,
  sessionTitle,
  placeholder,
  onSend,
  onUpload,
  onRemoveUpload,
  onStop,
  uploadedFiles,
  isThinking,
  streamingContent,
  errorMessage,
  onClearError,
  pdfSuggestion,
  pdfDefaults,
  onDismissPdfSuggestion,
  planDrafts,
  onConfirmPlan,
}: ChatViewProps) {
  const [inputValue, setInputValue] = useState('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const [pdfOpen, setPdfOpen] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfFileName, setPdfFileName] = useState<string>('cpet_report.pdf');
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<'cpet' | 'wearable'>('cpet');
  const isAnalysis = agentId === 'analysis';
  const isDiet = agentId === 'diet';
  const showUploadCard = agentId !== 'report' && agentId !== 'prescription';
  const quickCardCount = (showUploadCard ? 1 : 0) + (isAnalysis ? 2 : 0);
  const quickGridCols =
    quickCardCount >= 3 ? 'sm:grid-cols-3' : quickCardCount === 2 ? 'sm:grid-cols-2' : 'sm:grid-cols-1';

  const pdfLabel = pdfSuggestion === 'prescription' ? '运动处方 PDF' : 'CPET 报告 PDF';
  const pdfMissing = pdfDefaults?.missing ?? [];
  const pdfReady = Boolean(pdfSuggestion) && pdfDefaults?.payload;
  const pdfPayload = pdfDefaults?.payload;
  const dataSourceLabel = dataSource === 'cpet' ? 'CPET' : '手表';
  const requiredFieldCount = 11;
  const parsedCount = uploadedFiles?.filter((file) => file.status === 'parsed').length ?? 0;
  const failedCount = uploadedFiles?.filter((file) => file.status === 'failed').length ?? 0;
  const parseStatus = useMemo(() => {
    if (!uploadedFiles || uploadedFiles.length === 0) {
      return '未上传';
    }
    if (failedCount > 0) {
      return '存在失败';
    }
    if (parsedCount > 0) {
      return '已解析';
    }
    return '已上传';
  }, [failedCount, parsedCount, uploadedFiles]);
  const completeness = useMemo(() => {
    if (!pdfDefaults) {
      return null;
    }
    const ratio = Math.max(0, (requiredFieldCount - pdfMissing.length) / requiredFieldCount);
    return Math.round(ratio * 100);
  }, [pdfDefaults, pdfMissing.length]);
  const confidenceLabel = useMemo(() => {
    if (!pdfDefaults) {
      return '待评估';
    }
    if (pdfMissing.length <= 2) {
      return '高';
    }
    if (pdfMissing.length <= 5) {
      return '中';
    }
    return '低';
  }, [pdfDefaults, pdfMissing.length]);
  const summaryPayload =
    pdfPayload && typeof pdfPayload === 'object'
      ? (pdfPayload as Record<string, unknown>)
      : null;
  const summaryCpet = summaryPayload
    ? (summaryPayload['cpet_results'] as Record<string, unknown> | undefined)
    : undefined;
  const vo2PeakValue =
    typeof summaryCpet?.['vo2_peak'] === 'number'
      ? (summaryCpet?.['vo2_peak'] as number)
      : null;
  const riskItems = useMemo(() => {
    const items: string[] = [];
    if (failedCount > 0) {
      items.push('存在解析失败文件');
    }
    if (pdfMissing.length > 0) {
      items.push(`缺失字段：${pdfMissing.join('、')}`);
    }
    if (confidenceLabel === '低') {
      items.push('置信度偏低，建议补充数据');
    }
    return items;
  }, [confidenceLabel, failedCount, pdfMissing]);
  const pdfHint = useMemo(() => {
    if (!pdfSuggestion) {
      return '';
    }
    if (!pdfDefaults) {
      return '尚未识别到可生成 PDF 的结果。';
    }
    if (pdfMissing.length > 0) {
      return `缺少：${pdfMissing.join('、')}，将自动使用默认值`;
    }
    return '是否生成 PDF？';
  }, [pdfDefaults, pdfMissing, pdfSuggestion]);

  const thinkingIndicator = isThinking ? (
    <div className="flex justify-start gap-3">
      <div className="mt-0.5 w-9 h-9 rounded-full bg-gray-100 border border-gray-200 flex items-center justify-center flex-shrink-0">
        <Bot className="w-4 h-4 text-gray-500" />
      </div>
      <div className="rounded-2xl bg-gray-100 text-gray-600 px-4 py-3 text-sm max-w-[80%]">
        {streamingContent ? (
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {streamingContent}
            </ReactMarkdown>
            <span className="inline-block w-2 h-4 bg-gray-400 animate-pulse ml-1" />
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <span>思考中</span>
            <span className="flex items-center gap-1">
              <span className="thinking-dot" />
              <span className="thinking-dot delay-1" />
              <span className="thinking-dot delay-2" />
            </span>
          </div>
        )}
      </div>
    </div>
  ) : null;

  // Auto-scroll to bottom when new messages or streaming content
  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [messages, streamingContent, isThinking]);

  const resetPdfPreview = () => {
    if (pdfUrl) {
      URL.revokeObjectURL(pdfUrl);
    }
    setPdfUrl(null);
    setPdfError(null);
  };

  useEffect(() => {
    setPdfError(null);
    if (!pdfSuggestion) {
      setPdfOpen(false);
    }
  }, [pdfSuggestion]);

  useEffect(() => {
    if (!pdfSuggestion) {
      return;
    }
    setPdfFileName(
      pdfSuggestion === 'prescription' ? 'exercise_prescription.pdf' : 'cpet_report.pdf'
    );
  }, [pdfSuggestion]);

  useEffect(() => {
    return () => {
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [pdfUrl]);

  const handleGeneratePdf = async () => {
    if (!pdfSuggestion || !pdfPayload) {
      return;
    }
    resetPdfPreview();
    setPdfLoading(true);
    setPdfOpen(true);
    try {
      const apiBase = import.meta.env.VITE_API_BASE ?? '';
      const endpoint =
        pdfSuggestion === 'prescription' ? '/api/prescription/pdf' : '/api/reports/generate';
      const response = await fetch(`${apiBase}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(pdfPayload),
      });
      if (!response.ok) {
        throw new Error(`生成失败 (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const disposition = response.headers.get('Content-Disposition') || '';
      const match = disposition.match(/filename=([^;]+)/i);
      const filename = match ? match[1].replace(/\"/g, '') : pdfFileName;
      setPdfFileName(filename);
      setPdfUrl(url);
    } catch (error) {
      setPdfError(error instanceof Error ? error.message : '生成失败');
    } finally {
      setPdfLoading(false);
    }
  };

  const handleSend = () => {
    const trimmed = inputValue.trim();
    if (!trimmed) {
      return;
    }
    onSend(trimmed);
    setInputValue('');
  };

  const handleDismissPdf = () => {
    setPdfError(null);
    onDismissPdfSuggestion?.();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const handleGenerateNutritionPlan = () => {
    if (isThinking) return;
    onSend(
      '请直接调用 MCP 工具 generate_nutrition_plan 生成营养规划；如缺少体重/身高/年龄/性别，请先向我询问后再生成。'
    );
    setInputValue('');
  };

  return (
    <div className="flex-1 min-h-0 flex flex-col">
      <div className="flex-1 overflow-y-auto px-6 pt-6 pb-28 chat-scroll-container" ref={scrollContainerRef}>
        <div className="max-w-[760px] mx-auto">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-xs text-gray-400">当前会话</p>
              <h2 className="text-lg font-semibold text-gray-900">
                {sessionTitle ?? '新会话'}
              </h2>
            </div>
            <div className="flex items-center gap-2">
              {agentLabel && (
                <span className="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded-full inline-flex items-center gap-2">
                  <span>Agent | {agentLabel}</span>
                  {agentTag && (
                    <span className="px-1.5 py-0.5 rounded-full bg-gray-200 text-gray-700 text-[10px] leading-none">
                      {agentTag}
                    </span>
                  )}
                </span>
              )}
              <button
                type="button"
                onClick={() => {
                  if (pdfUrl) {
                    setPdfOpen(true);
                    return;
                  }
                  handleGeneratePdf();
                }}
                disabled={!pdfSuggestion || !pdfReady || pdfLoading}
                className={`px-3 py-1.5 rounded-full text-xs inline-flex items-center gap-2 border ${
                  pdfSuggestion && pdfReady
                    ? 'border-gray-200 text-gray-700 hover:border-gray-300'
                    : 'border-gray-100 text-gray-400'
                }`}
                title={pdfSuggestion ? '生成或查看 PDF' : '暂无可生成 PDF'}
              >
                <FileText className="w-3.5 h-3.5" />
                {pdfUrl ? '查看 PDF' : pdfLoading ? '生成中…' : 'PDF'}
              </button>
            </div>
          </div>

          {isAnalysis && (
            <div className="mb-6 rounded-2xl border border-gray-200 bg-white/70 px-4 py-3">
              <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600">
                <span className="px-2 py-1 rounded-full bg-gray-100">
                  数据源：{dataSourceLabel}
                </span>
                <span className="px-2 py-1 rounded-full bg-gray-100">
                  完整度：{completeness !== null ? `${completeness}%` : '待评估'}
                </span>
                <span className="px-2 py-1 rounded-full bg-gray-100">
                  解析状态：{parseStatus}
                </span>
                <span className="px-2 py-1 rounded-full bg-gray-100">
                  置信度：{confidenceLabel}
                </span>
              </div>
              <div className="mt-2 text-[11px] text-gray-400">AI 辅助结论需医师确认</div>
            </div>
          )}

          {planDrafts && planDrafts.length > 0 && (
            <div className="space-y-3 mb-6">
              {planDrafts.map((draft) => (
                <PlanDraftCard key={draft.id} draft={draft} onConfirm={onConfirmPlan} />
              ))}
            </div>
          )}

          {messages.length === 0 ? (
            <div className="space-y-6">
              {quickCardCount > 0 && (
                <div className={`grid gap-4 ${quickGridCols}`}>
                  {showUploadCard && (
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="rounded-2xl border border-gray-200 bg-white p-4 text-left hover:border-gray-300 transition-colors"
                    >
                      <div className="w-9 h-9 rounded-lg bg-gray-100 flex items-center justify-center text-gray-600">
                        <FileUp className="w-4 h-4" />
                      </div>
                      <div className="mt-3 text-sm font-medium text-gray-900">上传 CPET</div>
                      <div className="mt-1 text-xs text-gray-500">支持 PDF/CSV/JSON</div>
                    </button>
                  )}
                  {isAnalysis && (
                    <button
                      type="button"
                      onClick={() => setDataSource('wearable')}
                      className="rounded-2xl border border-gray-200 bg-white p-4 text-left hover:border-gray-300 transition-colors"
                    >
                      <div className="w-9 h-9 rounded-lg bg-gray-100 flex items-center justify-center text-gray-600">
                        <Watch className="w-4 h-4" />
                      </div>
                      <div className="mt-3 text-sm font-medium text-gray-900">连接手表</div>
                      <div className="mt-1 text-xs text-gray-500">同步运动与心率数据</div>
                    </button>
                  )}
                  {isAnalysis && (
                    <button
                      type="button"
                      onClick={() => {
                        setInputValue('请录入关键指标：VO2peak、HRmax、HRrest、METS、AT 时间。');
                        inputRef.current?.focus();
                      }}
                      className="rounded-2xl border border-gray-200 bg-white p-4 text-left hover:border-gray-300 transition-colors"
                    >
                      <div className="w-9 h-9 rounded-lg bg-gray-100 flex items-center justify-center text-gray-600">
                        <ClipboardList className="w-4 h-4" />
                      </div>
                      <div className="mt-3 text-sm font-medium text-gray-900">手动输入关键指标</div>
                      <div className="mt-1 text-xs text-gray-500">快速补全缺失字段</div>
                    </button>
                  )}
                </div>
              )}
              <div>
                <div className="text-xs text-gray-400 mb-2">示例问题</div>
                <div className="flex flex-wrap gap-2">
                  {['预测 AT', '估算 VO2peak', '生成处方建议'].map((example) => (
                    <button
                      key={example}
                      type="button"
                      onClick={() => {
                        setInputValue(example);
                        inputRef.current?.focus();
                      }}
                      className="px-3 py-1.5 rounded-full border border-gray-200 text-xs text-gray-600 hover:border-gray-300"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>
              {thinkingIndicator}
            </div>
          ) : (
            <div className="space-y-4">
              {isAnalysis && uploadedFiles && uploadedFiles.length > 0 && (
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-2xl border border-gray-200 bg-white px-4 py-3">
                    <div className="text-xs text-gray-400">结论卡</div>
                    <div className="mt-2 space-y-1 text-sm text-gray-700">
                      <div className="flex items-center justify-between">
                        <span>AT 时间</span>
                        <span className="text-gray-900">待评估</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>VO2peak</span>
                        <span className="text-gray-900">
                          {vo2PeakValue !== null ? `${vo2PeakValue} ml/kg/min` : '待评估'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>置信区间</span>
                        <span className="text-gray-900">—</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Weber 分级</span>
                        <span className="text-gray-900">待评估</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>数据质量</span>
                        <span className="text-gray-900">
                          {completeness !== null ? `${completeness}%` : '待评估'}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="rounded-2xl border border-gray-200 bg-white px-4 py-3">
                    <div className="text-xs text-gray-400">证据卡</div>
                    <div className="mt-2 text-sm text-gray-700">
                      AT 前后 60s 曲线摘要待解析，建议补充关键区段或波形截图。
                    </div>
                  </div>
                  <div className="rounded-2xl border border-gray-200 bg-white px-4 py-3">
                    <div className="text-xs text-gray-400">风险卡</div>
                    <div className="mt-2 space-y-1 text-sm text-gray-700">
                      {riskItems.length > 0 ? (
                        riskItems.map((item) => <div key={item}>{item}</div>)
                      ) : (
                        <div>暂未发现明显风险提示，可进一步检查噪声/异常值。</div>
                      )}
                    </div>
                  </div>
                </div>
              )}
              {messages.map((message) => {
                const isUser = message.role === 'user';
                return (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                    className={`flex ${isUser ? 'justify-end' : 'justify-start'} gap-3`}
                  >
                    {!isUser && (
                      <div className="mt-0.5 w-9 h-9 rounded-full bg-gray-100 border border-gray-200 flex items-center justify-center flex-shrink-0">
                        <Bot className="w-4 h-4 text-gray-500" />
                      </div>
                    )}
                    <div
                      className={`
                        max-w-[80%] text-sm leading-relaxed
                        ${isUser
                          ? 'rounded-2xl bg-gray-100 text-gray-900 px-4 py-3'
                          : 'text-gray-800'}
                      `}
                    >
                      {isUser ? (
                        <div>{message.content}</div>
                      ) : (
                        <div className="markdown-body">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                          </ReactMarkdown>
                        </div>
                      )}
                      <div className="mt-2 text-[10px] text-gray-400">
                        {message.timestamp}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
              {thinkingIndicator}
              {pdfSuggestion && (
                <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-700">
                  <div className="font-medium">{pdfLabel}</div>
                  <div className="text-xs text-gray-500 mt-1">{pdfHint}</div>
                  {pdfError && (
                    <div className="text-xs text-red-500 mt-2">{pdfError}</div>
                  )}
                  <div className="mt-3 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleGeneratePdf}
                      disabled={!pdfReady || pdfLoading}
                      className={`px-3 py-1.5 rounded-full text-xs ${
                        pdfReady ? 'bg-black text-white' : 'bg-gray-200 text-gray-400'
                      }`}
                    >
                      {pdfLoading ? '生成中…' : '生成 PDF'}
                    </button>
                    <button
                      type="button"
                      onClick={handleDismissPdf}
                      className="px-3 py-1.5 rounded-full border border-gray-200 text-xs text-gray-600 hover:border-gray-300"
                    >
                      稍后
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <Dialog
        open={pdfOpen}
        onOpenChange={(open) => {
          setPdfOpen(open);
          if (!open) {
            resetPdfPreview();
          }
        }}
      >
        <DialogContent className="max-w-5xl">
          <DialogHeader>
            <DialogTitle>{pdfLabel}</DialogTitle>
            <DialogDescription>
              已根据解析结果生成 PDF，可预览并下载。
            </DialogDescription>
          </DialogHeader>
          {pdfLoading && (
            <div className="text-sm text-gray-500">正在生成 PDF…</div>
          )}
          {pdfError && (
            <div className="text-sm text-red-500">{pdfError}</div>
          )}

          {pdfUrl && (
            <div className="mt-4 rounded-lg border border-gray-200 overflow-hidden">
              <iframe title="PDF 预览" src={pdfUrl} className="w-full h-[620px]" />
            </div>
          )}

          <DialogFooter className="gap-2 sm:gap-2">
            <button
              type="button"
              onClick={() => setPdfOpen(false)}
              className="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:border-gray-300"
            >
              关闭
            </button>
            {pdfUrl && (
              <a
                href={pdfUrl}
                download={pdfFileName}
                className="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-700 hover:border-gray-300"
              >
                下载
              </a>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="sticky bottom-0 w-full bg-white/95 backdrop-blur">
        <div className="max-w-[760px] mx-auto px-6 py-4">
          <div className="relative flex flex-col gap-4 p-6 bg-transparent rounded-3xl border border-gray-200">
            {errorMessage && (
              <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">
                <div className="flex items-start justify-between gap-4">
                  <div className="font-medium">请求失败</div>
                  {onClearError && (
                    <button
                      type="button"
                      onClick={onClearError}
                      className="text-xs text-red-600 hover:text-red-700"
                    >
                      清除
                    </button>
                  )}
                </div>
                <div className="mt-1 text-[11px] text-red-600 break-words">{errorMessage}</div>
              </div>
            )}
            {uploadedFiles && uploadedFiles.length > 0 && (
              <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                {uploadedFiles.map((file) => (
                  <span
                    key={file.id}
                    className="relative inline-flex items-center px-2 py-1 rounded-full pr-5 bg-gray-100 text-gray-600"
                  >
                    {file.name}
                    {file.status === 'parsed' ? ' · 已解析' : file.status === 'failed' ? ' · 失败' : ' · 已上传'}
                    {onRemoveUpload && (
                      <button
                        type="button"
                        title="删除"
                        onClick={(event) => {
                          event.stopPropagation();
                          onRemoveUpload(file.id);
                        }}
                        className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-white border border-gray-200 text-gray-500 hover:text-gray-700 hover:border-gray-300 flex items-center justify-center"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    )}
                  </span>
                ))}
              </div>
            )}
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder ?? '上传 CPET 报告或输入问题…'}
              rows={1}
              className="
                w-full min-h-[40px] max-h-[160px]
                bg-transparent text-base text-gray-900
                placeholder:text-gray-400 resize-none
                outline-none border-0 p-0
              "
            />
            <div className="flex flex-wrap gap-2">
              {['预测 AT', '估算 VO2peak', '生成处方建议'].map((chip) => (
                <button
                  key={chip}
                  type="button"
                  onClick={() => {
                    setInputValue(chip);
                    inputRef.current?.focus();
                  }}
                  className="px-3 py-1 rounded-full border border-gray-200 text-xs text-gray-600 hover:border-gray-300"
                >
                  {chip}
                </button>
              ))}
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <motion.button
                  whileHover={{ scale: 1.05, backgroundColor: 'rgba(0, 0, 0, 0.04)' }}
                  whileTap={{ scale: 0.95 }}
                  title="上传报告或原始数据"
                  onClick={() => fileInputRef.current?.click()}
                  className="w-8 h-8 flex items-center justify-center rounded-full border border-gray-200 text-gray-500 hover:border-gray-300 transition-colors duration-150"
                >
                  <Plus className="w-4 h-4" />
                </motion.button>
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept=".csv,.json,.txt,.pdf,application/pdf,text/csv,application/json,text/plain"
                  multiple
                  onChange={(event) => {
                    onUpload?.(event.target.files);
                    event.currentTarget.value = '';
                  }}
                />

                <motion.button
                  whileHover={{ scale: 1.02, backgroundColor: 'rgba(0, 0, 0, 0.04)' }}
                  whileTap={{ scale: 0.98 }}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-gray-200 text-sm text-gray-600 hover:border-gray-300 transition-colors duration-150"
                >
                  <Bot className="w-4 h-4" />
                  <span className="flex items-center gap-2">
                    <span>{agentLabel ? `Agent · ${agentLabel}` : '选择领域'}</span>
                    {agentLabel && agentTag && (
                      <span className="px-1.5 py-0.5 rounded-full bg-gray-200 text-gray-700 text-[10px] leading-none">
                        {agentTag}
                      </span>
                    )}
                  </span>
                </motion.button>
                {isAnalysis && (
                  <motion.button
                    whileHover={{ scale: 1.02, backgroundColor: 'rgba(0, 0, 0, 0.04)' }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => {
                      setInputValue('关键指标：VO2peak= , HRmax= , HRrest= , METS= , AT 时间= 。');
                      inputRef.current?.focus();
                    }}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-gray-200 text-xs text-gray-600 hover:border-gray-300 transition-colors duration-150"
                  >
                    <ClipboardList className="w-3.5 h-3.5" />
                    <span>关键指标快速填充</span>
                  </motion.button>
                )}
                {isDiet && (
                  <motion.button
                    whileHover={{ scale: 1.02, backgroundColor: 'rgba(0, 0, 0, 0.04)' }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleGenerateNutritionPlan}
                    disabled={isThinking}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-emerald-200 text-xs text-emerald-700 hover:border-emerald-300 transition-colors duration-150 disabled:opacity-50"
                  >
                    <Utensils className="w-3.5 h-3.5" />
                    <span>生成营养规划</span>
                  </motion.button>
                )}
              </div>

              <div className="flex items-center gap-2">
                {isAnalysis && (
                  <div className="flex items-center gap-1 rounded-full border border-gray-200 bg-white p-1 text-xs text-gray-600">
                    <button
                      type="button"
                      onClick={() => setDataSource('cpet')}
                      className={`px-2.5 py-1 rounded-full ${
                        dataSource === 'cpet' ? 'bg-black text-white' : 'text-gray-600'
                      }`}
                    >
                      CPET
                    </button>
                    <button
                      type="button"
                      onClick={() => setDataSource('wearable')}
                      className={`px-2.5 py-1 rounded-full ${
                        dataSource === 'wearable' ? 'bg-black text-white' : 'text-gray-600'
                      }`}
                    >
                      手表
                    </button>
                  </div>
                )}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <motion.button
                      whileHover={{ scale: 1.02, backgroundColor: 'rgba(0, 0, 0, 0.04)' }}
                      whileTap={{ scale: 0.98 }}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-full text-sm text-gray-600 hover:bg-gray-100 transition-colors duration-150"
                    >
                      <span>临床模式</span>
                      <ChevronDown className="w-4 h-4" />
                    </motion.button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-40">
                    <DropdownMenuItem>临床模式</DropdownMenuItem>
                    <DropdownMenuItem>科研模式</DropdownMenuItem>
                    <DropdownMenuItem>教学模式</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                <motion.button
                  whileHover={{ scale: 1.05, backgroundColor: isThinking ? '#ef4444' : inputValue ? '#333' : '#000' }}
                  whileTap={{ scale: 0.95 }}
                  onClick={isThinking ? onStop : handleSend}
                  className={`
                    w-8 h-8 flex items-center justify-center rounded-full
                    transition-colors duration-150
                    ${isThinking ? 'bg-red-500 text-white' : inputValue ? 'bg-black text-white' : 'bg-gray-200 text-gray-400'}
                  `}
                  disabled={!isThinking && !inputValue}
                  title={isThinking ? '停止生成' : '发送'}
                >
                  {isThinking ? <Square className="w-3 h-3" /> : <ArrowUp className="w-4 h-4" />}
                </motion.button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PlanDraftCard({
  draft,
  onConfirm,
}: {
  draft: PlanDraft;
  onConfirm?: (draftId: string) => void;
}) {
  const isExercise = draft.planType === 'exercise';
  const payload = (draft.payload ?? {}) as Record<string, unknown>;
  const goals = (payload['goals'] ?? {}) as Record<string, unknown>;
  const sessions = Array.isArray(payload['sessions']) ? (payload['sessions'] as Record<string, unknown>[]) : [];
  const macros = (payload['macros'] ?? {}) as Record<string, unknown>;
  const meals = Array.isArray(payload['meals']) ? (payload['meals'] as Record<string, unknown>[]) : [];
  const constraints = (payload['constraints'] ?? {}) as Record<string, unknown>;
  const mealRows = meals.map((meal, index) => {
    const mealType = typeof meal['meal_type'] === 'string' ? (meal['meal_type'] as string) : `餐次${index + 1}`;
    const kcal = meal['kcal'];
    const foods = Array.isArray(meal['foods']) ? (meal['foods'] as string[]).filter(Boolean) : [];
    return { mealType, kcal, foods, index };
  });

  const statusLabel = draft.status === 'confirmed' ? '已确认' : '待确认';

  return (
    <div className="rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-700">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-medium text-gray-900">{isExercise ? '运动处方草案' : '营养规划草案'}</div>
          <div className="text-xs text-gray-500 mt-1">{draft.summary}</div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-gray-500">{statusLabel}</span>
          {draft.status !== 'confirmed' && (
            <button
              type="button"
              onClick={() => onConfirm?.(draft.id)}
              className="px-2.5 py-1 rounded-full bg-black text-white text-xs"
            >
              确认保存
            </button>
          )}
        </div>
      </div>

      {draft.warnings?.length > 0 && (
        <div className="mt-2 text-xs text-amber-600">
          {draft.warnings.map((w) => (
            <div key={w}>{w}</div>
          ))}
        </div>
      )}

      {isExercise ? (
        <div className="mt-3 text-xs text-gray-600 space-y-1">
          <div>
            目标：步数 {String(goals['steps_target'] ?? '—')} · 时长 {String(goals['minutes_target'] ?? '—')} 分钟 ·
            消耗 {String(goals['kcal_target'] ?? '—')} kcal · 心率区间 {String(goals['hr_zone'] ?? '—')}
          </div>
          <div>计划条目：{sessions.length} 条</div>
        </div>
      ) : (
        <div className="mt-3 text-xs text-gray-600 space-y-1">
          <div>
            宏量：热量 {String(macros['kcal'] ?? '—')} kcal · 蛋白 {String(macros['protein_g'] ?? '—')} g ·
            碳水 {String(macros['carbs_g'] ?? '—')} g · 脂肪 {String(macros['fat_g'] ?? '—')} g
          </div>
          <div>餐次建议：{meals.length} 条</div>
          {mealRows.length > 0 && (
            <div className="space-y-1">
              {mealRows.map((meal) => (
                <div key={`${meal.mealType}-${meal.index}`}>
                  {meal.mealType}：{meal.kcal ? `${meal.kcal} kcal` : '—'}
                  {meal.foods.length > 0 ? ` · ${meal.foods.join('、')}` : ''}
                </div>
              ))}
            </div>
          )}
          <div>
            约束：控糖 {String(constraints['low_sugar'] ?? '—')} · 控盐 {String(constraints['low_salt'] ?? '—')} ·
            高纤维 {String(constraints['high_fiber'] ?? '—')}
          </div>
        </div>
      )}
    </div>
  );
}
