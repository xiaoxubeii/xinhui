import { motion } from 'framer-motion';
import type { ReactNode } from 'react';
import { FileText, Presentation, Table, Search, Users } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface TagItemProps {
  icon: ReactNode;
  label: string;
  badge?: string;
  delay: number;
}

const TagItem = ({ icon, label, badge, delay }: TagItemProps) => (
  <motion.button
    initial={{ y: 10, opacity: 0 }}
    animate={{ y: 0, opacity: 1 }}
    transition={{ duration: 0.3, delay: 0.4 + delay, ease: 'easeOut' }}
    whileHover={{ 
      scale: 1.02, 
      backgroundColor: '#f5f5f5',
      borderColor: '#d0d0d0'
    }}
    whileTap={{ scale: 0.98 }}
    className="
      flex items-center gap-2 px-4 py-2 
      bg-white border border-gray-200 rounded-full
      text-sm text-gray-700
      transition-colors duration-150
      hover:shadow-sm
    "
  >
    <span className="text-gray-500">{icon}</span>
    <span>{label}</span>
    {badge && (
      <Badge 
        variant="secondary" 
        className="text-[10px] px-1.5 py-0 h-4 bg-blue-50 text-blue-500 border-0 font-normal ml-0.5"
      >
        {badge}
      </Badge>
    )}
  </motion.button>
);

export function FeatureTags() {
  const tags = [
    { icon: <FileText className="w-4 h-4" />, label: 'CPET 报告解读' },
    { icon: <Presentation className="w-4 h-4" />, label: '运动处方' },
    { icon: <Search className="w-4 h-4" />, label: '运动健康' },
    { icon: <Table className="w-4 h-4" />, label: '食疗建议' },
    { icon: <Users className="w-4 h-4" />, label: '临床智能体', badge: 'Beta' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4, delay: 0.35 }}
      className="flex flex-wrap items-center justify-center gap-2 mt-6"
    >
      {tags.map((tag, index) => (
        <TagItem
          key={tag.label}
          icon={tag.icon}
          label={tag.label}
          badge={tag.badge}
          delay={index * 0.05}
        />
      ))}
    </motion.div>
  );
}
