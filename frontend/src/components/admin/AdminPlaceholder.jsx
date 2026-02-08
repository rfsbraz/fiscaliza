import { motion } from 'framer-motion'
import { Construction } from 'lucide-react'
import { tokens } from './AdminLayout'

// Placeholder for future admin pages
const AdminPlaceholder = ({ title, description, icon: Icon = Construction }) => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex items-center justify-center min-h-[60vh]"
    >
      <div className="text-center">
        <div
          className="w-16 h-16 rounded-lg mx-auto mb-4 flex items-center justify-center"
          style={{
            backgroundColor: tokens.colors.bg.tertiary,
            border: `1px dashed ${tokens.colors.border.primary}`
          }}
        >
          <Icon className="h-8 w-8" style={{ color: tokens.colors.text.muted }} />
        </div>
        <h2
          className="text-lg font-medium mb-2"
          style={{ color: tokens.colors.text.primary }}
        >
          {title}
        </h2>
        <p
          className="text-sm max-w-md"
          style={{ color: tokens.colors.text.muted }}
        >
          {description}
        </p>
        <div
          className="mt-6 inline-flex items-center gap-2 px-4 py-2 rounded text-xs uppercase tracking-wider"
          style={{
            backgroundColor: tokens.colors.accent.tertiary + '15',
            color: tokens.colors.accent.tertiary,
            border: `1px solid ${tokens.colors.accent.tertiary}30`
          }}
        >
          <Construction className="h-3 w-3" />
          Coming Soon
        </div>
      </div>
    </motion.div>
  )
}

export default AdminPlaceholder
