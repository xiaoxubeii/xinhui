import { useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { motion } from 'framer-motion';
import { Plus, Bot, ChevronDown, ArrowUp } from 'lucide-react';
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
}

export function SearchBox({
  placeholder,
  agentLabel,
  agentTag,
  onSubmit,
  onUpload,
  uploadedFiles,
}: SearchBoxProps) {
  const [inputValue, setInputValue] = useState('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

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
        `}
      >
        {uploadedFiles && uploadedFiles.length > 0 && (
          <div className="flex flex-wrap gap-2 text-xs text-gray-500">
            {uploadedFiles.map((file) => (
              <span
                key={file.id}
                className="px-2 py-1 rounded-full bg-gray-100 text-gray-600"
              >
                {file.name}
                {file.status === 'parsed' ? ' · 已解析' : file.status === 'failed' ? ' · 失败' : ' · 已上传'}
              </span>
            ))}
          </div>
        )}

        {/* Input Area */}
        <textarea
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
    </motion.div>
  );
}
