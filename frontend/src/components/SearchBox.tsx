import { useRef, useState, useEffect } from 'react';
import type { KeyboardEvent } from 'react';
import { motion } from 'framer-motion';
import { Plus, Bot, ChevronDown, ArrowUp, Sparkles, X } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface SearchBoxProps {
  placeholder?: string;
  agentLabel?: string | null;
  agentTag?: string | null;
  onSubmit: (value: string) => void;
  onUpload?: (files: FileList | null) => void;
  uploadedFiles?: { id: string; name: string; status: string }[];
  onRemoveUpload?: (id: string) => void;
}

const EXAMPLE_PROMPTS = [
  '分析这份 CPET 报告的关键指标',
  '根据数据生成运动处方',
  '评估患者的运动风险等级',
  '解读 VO2peak 和无氧阈数据',
];

export function SearchBox({
  placeholder,
  agentLabel,
  agentTag,
  onSubmit,
  onUpload,
  uploadedFiles,
  onRemoveUpload,
}: SearchBoxProps) {
  const [inputValue, setInputValue] = useState('');
  const [currentExample, setCurrentExample] = useState(0);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Rotate example prompts
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentExample((prev) => (prev + 1) % EXAMPLE_PROMPTS.length);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [inputValue]);

  const handleSend = () => {
    const trimmed = inputValue.trim();
    if (!trimmed) {
      return;
    }
    onSubmit(trimmed);
    setInputValue('');
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const handleExampleClick = () => {
    setInputValue(EXAMPLE_PROMPTS[currentExample]);
    textareaRef.current?.focus();
  };

  return (
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, delay: 0.2, ease: 'easeOut' }}
      className="w-full max-w-[680px] mx-auto"
    >
      <div
        className={`
          relative flex flex-col gap-4 p-6
          bg-transparent rounded-3xl border
          transition-all duration-200 border-gray-200
          focus-within:border-gray-300 focus-within:shadow-sm
        `}
      >
        {uploadedFiles && uploadedFiles.length > 0 && (
          <div className="flex flex-wrap gap-2 text-xs text-gray-500">
            {uploadedFiles.map((file) => (
              <span
                key={file.id}
                className={`relative inline-flex items-center px-2 py-1 rounded-full pr-5 ${
                  file.status === 'parsed'
                    ? 'bg-green-50 text-green-700'
                    : file.status === 'failed'
                    ? 'bg-red-50 text-red-700'
                    : 'bg-gray-100 text-gray-600'
                }`}
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

        {/* Input Area */}
        <textarea
          ref={textareaRef}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder ?? '上传 CPET 报告或输入问题…'}
          className="
            w-full min-h-[40px] max-h-[200px]
            bg-transparent text-base text-gray-900
            placeholder:text-gray-400 resize-none
            outline-none border-0 p-0
          "
          rows={1}
        />

        {/* Example prompt hint */}
        {!inputValue && (
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            onClick={handleExampleClick}
            className="flex items-center gap-2 text-xs text-gray-400 hover:text-gray-600 transition-colors self-start"
          >
            <Sparkles className="w-3 h-3" />
            <span>试试：{EXAMPLE_PROMPTS[currentExample]}</span>
          </motion.button>
        )}

        {/* Bottom Controls */}
        <div className="flex items-center justify-between">
          {/* Left Buttons */}
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
          </div>

          {/* Right Controls */}
          <div className="flex items-center gap-2">
            {/* Model Selector */}
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

            {/* Send Button */}
            <motion.button
              whileHover={{ scale: 1.05, backgroundColor: inputValue ? '#333' : '#000' }}
              whileTap={{ scale: 0.95 }}
              onClick={handleSend}
              className={`
                w-8 h-8 flex items-center justify-center rounded-full
                transition-colors duration-150
                ${inputValue ? 'bg-black text-white' : 'bg-gray-200 text-gray-400'}
              `}
              disabled={!inputValue}
            >
              <ArrowUp className="w-4 h-4" />
            </motion.button>
          </div>
        </div>
      </div>

      {/* Keyboard hint */}
      <div className="mt-2 text-center text-xs text-gray-400">
        按 Enter 发送，Shift + Enter 换行
      </div>
    </motion.div>
  );
}
