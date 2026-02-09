import { motion } from 'framer-motion';
import { useState } from 'react';
import type { ReactNode } from 'react';
import {
  Plus,
  Clock,
  Info,
  FolderOpen,
  MessageSquare,
  User,
  Heart,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';

export type AgentId = 'report' | 'analysis' | 'health' | 'diet' | 'clinical' | 'prescription';

interface AgentNavItem {
  id: AgentId;
  label: string;
  icon: ReactNode;
  tag?: string;
}

interface SessionSummary {
  id: string;
  title: string;
  agentId: AgentId | null;
}

interface SidebarItemProps {
  icon: ReactNode;
  label: string;
  badge?: string;
  shortcut?: string;
  active?: boolean;
  disabled?: boolean;
  collapsed?: boolean;
  onClick?: () => void;
}

const SidebarItem = ({ icon, label, badge, shortcut, active, disabled, collapsed, onClick }: SidebarItemProps) => (
  <motion.button
    whileHover={{ backgroundColor: 'rgba(0, 0, 0, 0.04)' }}
    whileTap={{ scale: 0.98 }}
    onClick={onClick}
    title={label}
    aria-label={label}
    className={`
      w-full flex items-center gap-3 py-2 rounded-lg text-sm transition-colors duration-150
      ${collapsed ? 'justify-center px-2' : 'px-3'}
      ${active ? 'bg-black/5 text-black' : 'text-gray-900'}
      ${disabled ? 'opacity-50 pointer-events-none' : ''}
    `}
  >
    <span className="flex-shrink-0 w-5 h-5 flex items-center justify-center text-gray-800">
      {icon}
    </span>
    {!collapsed && (
      <>
        <span className="flex-1 text-left">{label}</span>
        {badge && (
          <Badge
            variant="secondary"
            className="text-[10px] px-1.5 py-0 h-4 bg-blue-50 text-blue-500 border-0 font-normal"
          >
            {badge}
          </Badge>
        )}
        {shortcut && (
          <span className="text-xs text-gray-400 flex items-center gap-0.5">
            <kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px]">Ctrl</kbd>
            <kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px]">K</kbd>
          </span>
        )}
      </>
    )}
  </motion.button>
);

const SidebarSection = ({ title, children, collapsed }: { title?: string; children: ReactNode; collapsed?: boolean }) => (
  <div className="mb-4">
    {title && !collapsed && (
      <div className="px-3 py-2 text-xs text-gray-400 font-medium">{title}</div>
    )}
    <div className="space-y-0.5">{children}</div>
  </div>
);

interface SidebarProps {
  agents: AgentNavItem[];
  activeAgentId: AgentId;
  activeView?: 'chat' | 'library' | 'account';
  sessions: SessionSummary[];
  activeSessionId: string | null;
  onSelectAgent: (id: AgentId) => void;
  onSelectView?: (view: 'chat' | 'library' | 'account') => void;
  onNewSession: () => void;
  onSelectSession: (id: string) => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

const sessionBadgeMap: Record<AgentId, string> = {
  report: '报告',
  analysis: '分析',
  health: '健康',
  diet: '食疗',
  clinical: '临床',
  prescription: '处方',
};

export function Sidebar({
  agents,
  activeAgentId,
  activeView = 'chat',
  sessions,
  activeSessionId,
  onSelectAgent,
  onSelectView,
  onNewSession,
  onSelectSession,
  collapsed,
  onToggleCollapse,
}: SidebarProps) {
  const [logoHover, setLogoHover] = useState(false);

  return (
    <motion.aside
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className={`
        fixed left-0 top-0 h-full bg-[#f9f9f9] flex flex-col z-50
        ${collapsed ? 'w-[72px]' : 'w-[240px]'}
      `}
    >
      {/* Logo */}
      <div className={`p-4 flex items-center ${collapsed ? 'justify-center' : 'justify-between'}`}>
        {collapsed ? (
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onMouseEnter={() => setLogoHover(true)}
            onMouseLeave={() => setLogoHover(false)}
            onClick={onToggleCollapse}
            title={logoHover ? '展开导航' : '导航'}
            aria-label="展开导航"
            className={`w-8 h-8 rounded-lg flex items-center justify-center cursor-pointer ${
              logoHover ? 'bg-transparent text-gray-700' : 'bg-black text-white'
            }`}
          >
            {logoHover ? (
              <PanelLeftOpen className="w-4 h-4" />
            ) : (
              <Heart className="w-4 h-4" />
            )}
          </motion.button>
        ) : (
          <motion.div
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="w-8 h-8 bg-black rounded-lg flex items-center justify-center cursor-pointer"
          >
            <Heart className="w-4 h-4 text-white" />
          </motion.div>
        )}
        {!collapsed && (
          <motion.button
            whileHover={{ scale: 1.02, backgroundColor: 'rgba(0, 0, 0, 0.04)' }}
            whileTap={{ scale: 0.98 }}
            onClick={onToggleCollapse}
            title="收起导航"
            className="w-8 h-8 flex items-center justify-center rounded-lg border border-gray-200 text-gray-500 hover:text-gray-700 hover:border-gray-300 transition-colors duration-150"
          >
            <PanelLeftClose className="w-4 h-4" />
          </motion.button>
        )}
      </div>

      {/* New Chat Button */}
      <div className={`${collapsed ? 'px-2' : 'px-3'} mb-4`}>
        <motion.button
          whileHover={{ backgroundColor: 'rgba(0, 0, 0, 0.04)' }}
          whileTap={{ scale: 0.98 }}
          onClick={onNewSession}
          className={`
            w-full flex items-center rounded-lg text-sm text-gray-900 border border-gray-200 bg-white hover:border-gray-300 transition-all duration-150
            ${collapsed ? 'justify-center px-2 py-2' : 'gap-3 px-3 py-2'}
          `}
        >
          <Plus className="w-4 h-4 text-gray-800" />
          {!collapsed && (
            <>
              <span className="flex-1 text-left">新建会话</span>
              <span className="text-xs text-gray-400 flex items-center gap-0.5">
                <kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px]">Ctrl</kbd>
                <kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px]">K</kbd>
              </span>
            </>
          )}
        </motion.button>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto px-2">
        <SidebarSection title="领域入口" collapsed={collapsed}>
          {agents.map((agent) => (
            <SidebarItem
              key={agent.id}
              icon={agent.icon}
              label={agent.label}
              badge={agent.tag}
              collapsed={collapsed}
              active={activeView === 'chat' && activeAgentId === agent.id}
              onClick={() => onSelectAgent(agent.id)}
            />
          ))}
        </SidebarSection>

        <SidebarSection title="资料库" collapsed={collapsed}>
          <SidebarItem
            icon={<FolderOpen className="w-4 h-4" />}
            label="我的上传"
            collapsed={collapsed}
            active={activeView === 'library'}
            onClick={() => onSelectView?.('library')}
          />
        </SidebarSection>

        <SidebarSection title="历史会话" collapsed={collapsed}>
          {sessions.length === 0 ? (
            <SidebarItem icon={<Clock className="w-4 h-4" />} label="暂无历史会话" disabled collapsed={collapsed} />
          ) : (
            sessions.map((session) => (
              <SidebarItem
                key={session.id}
                icon={<Clock className="w-4 h-4" />}
                label={session.title}
                badge={session.agentId ? sessionBadgeMap[session.agentId] : undefined}
                collapsed={collapsed}
                active={activeSessionId === session.id}
                onClick={() => onSelectSession(session.id)}
              />
            ))
          )}
        </SidebarSection>
      </div>

      {/* Footer Links */}
      <div className="p-2">
        <SidebarSection collapsed={collapsed}>
          <SidebarItem icon={<Info className="w-4 h-4" />} label="使用说明" collapsed={collapsed} />
          <SidebarItem icon={<MessageSquare className="w-4 h-4" />} label="用户反馈" collapsed={collapsed} />
          <SidebarItem
            icon={<User className="w-4 h-4" />}
            label="账号与合规"
            collapsed={collapsed}
            active={activeView === 'account'}
            onClick={() => onSelectView?.('account')}
          />
        </SidebarSection>
      </div>
    </motion.aside>
  );
}
