import { SearchBox } from '@/components/SearchBox';

interface AgentLandingViewProps {
  title: string;
  agentLabel?: string | null;
  placeholder?: string | null;
  onSend: (value: string) => void;
  onUpload?: (files: FileList | null) => void;
  uploadedFiles?: { id: string; name: string; status: string }[];
  onRemoveUpload?: (id: string) => void;
}

export function AgentLandingView({
  title,
  agentLabel,
  placeholder,
  onSend,
  onUpload,
  uploadedFiles,
  onRemoveUpload,
}: AgentLandingViewProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-14">
      <div className="w-full max-w-[720px] flex flex-col items-center gap-8 -mt-10">
        <div className="kimi-title text-5xl md:text-6xl font-semibold tracking-tight text-gray-900">
          {title}
        </div>
        <SearchBox
          placeholder={placeholder ?? undefined}
          agentLabel={agentLabel}
          onSubmit={onSend}
          onUpload={onUpload}
          uploadedFiles={uploadedFiles}
          onRemoveUpload={onRemoveUpload}
        />
      </div>
    </div>
  );
}
