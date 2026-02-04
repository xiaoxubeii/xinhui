import { motion } from 'framer-motion';

export function Footer() {
  return (
    <motion.footer
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4, delay: 0.8 }}
      className="mt-auto py-6 text-center"
    >
      <p className="text-xs text-gray-400 mb-2">
        本系统为临床辅助建议，不能替代医生诊断
      </p>
      <p className="text-xs text-gray-400">
        © 2026 心衡智问
      </p>
      <div className="flex items-center justify-center gap-4 mt-2">
        <a 
          href="#" 
          className="text-xs text-gray-400 hover:text-gray-600 hover:underline transition-colors duration-150"
        >
          隐私与合规
        </a>
        <a 
          href="#" 
          className="text-xs text-gray-400 hover:text-gray-600 hover:underline transition-colors duration-150"
        >
          使用条款
        </a>
        <a 
          href="#" 
          className="text-xs text-gray-400 hover:text-gray-600 hover:underline transition-colors duration-150"
        >
          联系我们
        </a>
      </div>
    </motion.footer>
  );
}
