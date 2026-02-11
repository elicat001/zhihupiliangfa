import React, { useState, useEffect } from 'react';
import { Input, Card, Row, Col, Typography } from 'antd';

const { TextArea } = Input;
const { Text } = Typography;

interface MarkdownEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  height?: number;
}

const MarkdownEditor: React.FC<MarkdownEditorProps> = ({ value = '', onChange, height = 400 }) => {
  const [content, setContent] = useState(value);

  // Sync external value changes
  useEffect(() => {
    setContent(value);
  }, [value]);

  const handleChange = (val: string) => {
    setContent(val);
    onChange?.(val);
  };

  // Simple markdown to HTML (basic support)
  const renderMarkdown = (md: string): string => {
    return md
      .replace(/^### (.*$)/gm, '<h3>$1</h3>')
      .replace(/^## (.*$)/gm, '<h2>$1</h2>')
      .replace(/^# (.*$)/gm, '<h1>$1</h1>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/^> (.*$)/gm, '<blockquote style="border-left: 3px solid #1677ff; padding-left: 12px; color: #a0a0a0;">$1</blockquote>')
      .replace(/^- (.*$)/gm, '<li>$1</li>')
      .replace(/^---$/gm, '<hr style="border-color: #2a2a3e" />')
      .replace(/\n/g, '<br/>');
  };

  return (
    <Row gutter={16}>
      <Col span={12}>
        <Card
          size="small"
          title={<Text style={{ color: '#e8e8e8', fontSize: 12 }}>编辑</Text>}
          style={{ background: '#1f1f1f', borderColor: '#2a2a3e' }}
          headStyle={{ borderBottom: '1px solid #2a2a3e', padding: '0 12px', minHeight: 32 }}
          bodyStyle={{ padding: 0 }}
        >
          <TextArea
            value={content}
            onChange={(e) => handleChange(e.target.value)}
            style={{
              height,
              background: '#141414',
              border: 'none',
              color: '#d0d0d0',
              fontFamily: 'monospace',
              fontSize: 13,
              resize: 'none',
            }}
          />
        </Card>
      </Col>
      <Col span={12}>
        <Card
          size="small"
          title={<Text style={{ color: '#e8e8e8', fontSize: 12 }}>预览</Text>}
          style={{ background: '#1f1f1f', borderColor: '#2a2a3e' }}
          headStyle={{ borderBottom: '1px solid #2a2a3e', padding: '0 12px', minHeight: 32 }}
          bodyStyle={{ padding: 12, height, overflowY: 'auto' }}
        >
          <div
            style={{ color: '#d0d0d0', lineHeight: 1.8, fontSize: 14 }}
            dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
          />
        </Card>
      </Col>
    </Row>
  );
};

export default MarkdownEditor;
