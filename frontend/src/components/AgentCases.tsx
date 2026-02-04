import { motion } from 'framer-motion';
import { ChevronRight } from 'lucide-react';

interface CaseCardProps {
  image: string;
  title: string;
  delay: number;
}

const CaseCard = ({ image, title, delay }: CaseCardProps) => (
  <motion.a
    href="#"
    initial={{ y: 20, opacity: 0 }}
    animate={{ y: 0, opacity: 1 }}
    transition={{ duration: 0.4, delay: 0.6 + delay, ease: 'easeOut' }}
    whileHover={{ 
      scale: 1.02,
      boxShadow: '0 8px 30px rgba(0, 0, 0, 0.12)'
    }}
    whileTap={{ scale: 0.98 }}
    className="
      block bg-white rounded-xl overflow-hidden
      border border-gray-100
      transition-shadow duration-200
      cursor-pointer
    "
  >
    <div className="h-[120px] overflow-hidden">
      <img 
        src={image} 
        alt={title}
        className="w-full h-full object-cover transition-transform duration-300 hover:scale-105"
      />
    </div>
    <div className="p-3">
      <p className="text-sm text-gray-700 line-clamp-2">{title}</p>
    </div>
  </motion.a>
);

export function AgentCases() {
  const cases = [
    {
      image: 'https://images.unsplash.com/photo-1611224923853-80b023f02d71?w=400&h=200&fit=crop',
      title: '上传 CPET 报告，自动生成解读摘要'
    },
    {
      image: 'https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=400&h=200&fit=crop',
      title: '一键生成个性化运动处方与 PDF'
    },
    {
      image: 'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=200&fit=crop',
      title: '基于 AT/VO2 结果给出健康与食疗建议'
    }
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4, delay: 0.55 }}
      className="w-full max-w-[680px] mx-auto mt-12"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-900">CPET 应用案例</h3>
        <motion.a
          href="#"
          whileHover={{ x: 2 }}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 transition-colors duration-150"
        >
          <span>更多</span>
          <ChevronRight className="w-4 h-4" />
        </motion.a>
      </div>

      {/* Cards Grid */}
      <div className="grid grid-cols-3 gap-4">
        {cases.map((item, index) => (
          <CaseCard
            key={item.title}
            image={item.image}
            title={item.title}
            delay={index * 0.1}
          />
        ))}
      </div>
    </motion.div>
  );
}
