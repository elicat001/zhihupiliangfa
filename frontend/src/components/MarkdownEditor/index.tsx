import React, { useState, useEffect } from 'react';
import { Input, Card, Row, Col, Typography } from 'antd';
import { colors } from '../../styles/theme';

const { TextArea } = Input;
const { Text } = Typography;

interface MarkdownEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  height?: number;
}

const MarkdownEditor: React.FC<MarkdownEditorProps> = ({ value = '', onChange, height = 400 }) => {
  const [content, setContent] = useState(value);

  useEffect(() => {
    setContent(value);
  }, [value]);

  const handleChange = (val: string) => {
    setContent(val);
    onChange?.(val);
  };

  const renderMarkdown = (md: string): string => {
    return md
      .replace(/^### (.*$)/gm, '<h3>$1</h3>')
      .replace(/^## (.*$)/gm, '<h2>$1</h2>')
      .replace(/^# (.*$)/gm, '<h1>$1</h1>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/^> (.*$)/gm, `<blockquote style="border-left: 3px solid ${colors.primary}; padding-left: 12px; color: ${colors.textSecondary};">$1</blockquote>`)
      .replace(/^- (.*$)/gm, '<li>$1</li>')
      .replace(/^---$/gm, `<hr style="border-color: ${colors.border}" />`)
      .replace(/\n/g, '<br/>');
  };

  return (
    <Row gutter={16}>
      <Col span={12}>
        <Card
          size="small"
          title={<Text style={{ color: colors.textPrimary, fontSize: 12 }}>编辑</Text>}
          style={{ background: colors.bgContainer, borderColor: colors.border }}
          styles={{
            header: { borderBottom: `1px solid ${colors.border}`, padding: '0 12px', minHeight: 32 },
            body: { padding: 0 },
          }}
        >
          <TextArea
            value={content}
            onChange={(e) => handleChange(e.target.value)}
            style={{
              height,
              background: colors.bgInput,
              border: 'none',
              color: colors.textPrimary,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 13,
              resize: 'none',
            }}
          />
        </Card>
      </Col>
      <Col span={12}>
        <Card
          size="small"
          title={<Text style={{ color: colors.textPrimary, fontSize: 12 }}>预览</Text>}
          style={{ background: colors.bgContainer, borderColor: colors.border }}
          styles={{
            header: { borderBottom: `1px solid ${colors.border}`, padding: '0 12px', minHeight: 32 },
            body: { padding: 12, height, overflowY: 'auto' as const },
          }}
        >
          <div
            style={{ color: colors.textPrimary, lineHeight: 1.8, fontSize: 14 }}
            dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
          />
        </Card>
      </Col>
    </Row>
  );
};

export default MarkdownEditor;
