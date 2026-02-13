import React, { useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Button,
  Row,
  Col,
  Divider,
  Typography,
  Space,
  Spin,
  message,
  Tabs,
  Alert,
} from 'antd';
import {
  SettingOutlined,
  ApiOutlined,
  SafetyCertificateOutlined,
  GlobalOutlined,
  SaveOutlined,
  UndoOutlined,
  RobotOutlined,
  SendOutlined,
  ChromeOutlined,
} from '@ant-design/icons';
import { useSettingsStore } from '../../stores/settingsStore';

const { Title, Text, Paragraph } = Typography;

/** AI提供商选项（需与后端支持的提供商一致） */
const aiProviders = [
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'OpenAI', value: 'openai' },
  { label: 'Claude', value: 'claude' },
  { label: 'Google Gemini', value: 'gemini' },
  { label: '通义千问 (Qwen)', value: 'qwen' },
  { label: '智谱 GLM', value: 'zhipu' },
  { label: '月之暗面 Kimi', value: 'moonshot' },
  { label: '豆包 (Doubao)', value: 'doubao' },
];

const Settings: React.FC = () => {
  const {
    settings,
    loading,
    saving,
    dirty,
    fetchSettings,
    updateSettings,
    setLocalSettings,
    resetSettings,
  } = useSettingsStore();

  const [aiForm] = Form.useForm();
  const [publishForm] = Form.useForm();
  const [browserForm] = Form.useForm();

  useEffect(() => {
    fetchSettings().catch(() => {
      // 使用默认值
    });
  }, []);

  // 当设置加载完成时，同步到表单
  useEffect(() => {
    if (settings) {
      aiForm.setFieldsValue(settings.ai_config);
      publishForm.setFieldsValue(settings.publish_strategy);
      browserForm.setFieldsValue(settings.browser_config);
    }
  }, [settings]);

  /** 保存AI配置 */
  const handleSaveAI = async () => {
    try {
      const values = await aiForm.validateFields();
      await updateSettings({ ai_config: values });
      message.success('AI 配置保存成功');
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error('保存失败');
    }
  };

  /** 保存发布策略 */
  const handleSavePublish = async () => {
    try {
      const values = await publishForm.validateFields();
      await updateSettings({ publish_strategy: values });
      message.success('发文策略保存成功');
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error('保存失败');
    }
  };

  /** 保存浏览器配置 */
  const handleSaveBrowser = async () => {
    try {
      const values = await browserForm.validateFields();
      await updateSettings({ browser_config: values });
      message.success('浏览器配置保存成功');
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error('保存失败');
    }
  };

  /** 卡片通用样式 */
  const cardStyle: React.CSSProperties = {
    background: '#1f1f1f',
    borderColor: '#2a2a3e',
    borderRadius: 12,
    marginBottom: 16,
  };

  const headStyle: React.CSSProperties = {
    borderBottom: '1px solid #2a2a3e',
  };

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '60vh',
        }}
      >
        <Spin size="large" tip="加载设置..." />
      </div>
    );
  }

  /** AI配置标签页 */
  const aiConfigContent = (
    <Card
      title={
        <span style={{ color: '#e8e8e8' }}>
          <RobotOutlined style={{ marginRight: 8, color: '#1677ff' }} />
          AI API 配置
        </span>
      }
      style={cardStyle}
      headStyle={headStyle}
    >
      <Alert
        message="请确保已在对应AI服务商处获取API Key"
        type="info"
        showIcon
        style={{ marginBottom: 20, background: '#111a2c', borderColor: '#15325b' }}
      />

      <Form
        form={aiForm}
        layout="vertical"
        initialValues={settings.ai_config}
      >
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item
              label="AI 服务提供商"
              name="provider"
              rules={[{ required: true, message: '请选择提供商' }]}
            >
              <Select options={aiProviders} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item
              label="模型名称"
              name="model"
              rules={[{ required: true, message: '请输入模型名称' }]}
            >
              <Input placeholder="如 gpt-4, deepseek-chat, glm-4" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          label="API Key"
          name="api_key"
          rules={[{ required: true, message: '请输入API Key' }]}
        >
          <Input.Password
            placeholder="sk-xxxxxxxxxxxx"
            style={{ background: '#141414', borderColor: '#2a2a3e' }}
          />
        </Form.Item>

        <Form.Item
          label="API Base URL"
          name="base_url"
          rules={[{ required: true, message: '请输入API地址' }]}
        >
          <Input
            placeholder="https://api.openai.com/v1"
            style={{ background: '#141414', borderColor: '#2a2a3e' }}
          />
        </Form.Item>

        <Row gutter={16}>
          <Col xs={12}>
            <Form.Item label="Temperature（创造力）" name="temperature">
              <InputNumber
                min={0}
                max={2}
                step={0.1}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
          <Col xs={12}>
            <Form.Item label="Max Tokens" name="max_tokens">
              <InputNumber
                min={256}
                max={32000}
                step={256}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={saving}
            onClick={handleSaveAI}
            style={{ borderRadius: 6 }}
          >
            保存 AI 配置
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );

  /** 发文策略标签页 */
  const publishStrategyContent = (
    <Card
      title={
        <span style={{ color: '#e8e8e8' }}>
          <SendOutlined style={{ marginRight: 8, color: '#52c41a' }} />
          发文策略配置
        </span>
      }
      style={cardStyle}
      headStyle={headStyle}
    >
      <Alert
        message="合理配置发文策略可以有效降低被风控的风险"
        type="warning"
        showIcon
        style={{ marginBottom: 20, background: '#2b2111', borderColor: '#594214' }}
      />

      <Form
        form={publishForm}
        layout="vertical"
        initialValues={settings.publish_strategy}
      >
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item label="默认发布方式" name="default_mode">
              <Select
                options={[
                  { label: '立即发布', value: 'immediate' },
                  { label: '定时发布', value: 'scheduled' },
                ]}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item
              label="每日发布上限"
              name="daily_limit"
              rules={[{ required: true, message: '请输入每日上限' }]}
              tooltip="单个账号每日最大发文数量，防止被风控"
            >
              <InputNumber
                min={1}
                max={100}
                style={{ width: '100%' }}
                addonAfter="篇/天"
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item
              label="发布最小间隔"
              name="interval_minutes"
              rules={[{ required: true, message: '请输入间隔时间' }]}
              tooltip="两次发文之间的最小时间间隔"
            >
              <InputNumber
                min={1}
                max={1440}
                style={{ width: '100%' }}
                addonAfter="分钟"
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item
              label="失败最大重试次数"
              name="max_retries"
              rules={[{ required: true, message: '请输入重试次数' }]}
            >
              <InputNumber
                min={0}
                max={10}
                style={{ width: '100%' }}
                addonAfter="次"
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          label="重试间隔"
          name="retry_delay_seconds"
          tooltip="发布失败后等待多久重试"
        >
          <InputNumber
            min={10}
            max={3600}
            style={{ width: '100%' }}
            addonAfter="秒"
          />
        </Form.Item>

        <Form.Item>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={saving}
            onClick={handleSavePublish}
            style={{ borderRadius: 6, background: '#52c41a', borderColor: '#52c41a' }}
          >
            保存发文策略
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );

  /** 浏览器配置标签页 */
  const browserConfigContent = (
    <Card
      title={
        <span style={{ color: '#e8e8e8' }}>
          <ChromeOutlined style={{ marginRight: 8, color: '#722ed1' }} />
          浏览器配置
        </span>
      }
      style={cardStyle}
      headStyle={headStyle}
    >
      <Form
        form={browserForm}
        layout="vertical"
        initialValues={settings.browser_config}
      >
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item
              label="无头模式"
              name="headless"
              valuePropName="checked"
              tooltip="无头模式下浏览器不显示窗口，资源消耗更低"
            >
              <Switch checkedChildren="开启" unCheckedChildren="关闭" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item
              label="浏览器启动超时"
              name="launch_timeout"
              tooltip="浏览器启动的最大等待时间"
            >
              <InputNumber
                min={5000}
                max={120000}
                step={1000}
                style={{ width: '100%' }}
                addonAfter="毫秒"
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item
              label="页面操作超时"
              name="action_timeout"
              tooltip="单个页面操作的最大等待时间"
            >
              <InputNumber
                min={3000}
                max={60000}
                step={1000}
                style={{ width: '100%' }}
                addonAfter="毫秒"
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          label="自定义 User-Agent"
          name="user_agent"
          tooltip="留空则使用默认值，自定义可降低被检测风险"
        >
          <Input
            placeholder="留空使用默认 User-Agent"
            style={{ background: '#141414', borderColor: '#2a2a3e' }}
          />
        </Form.Item>

        <Form.Item
          label="代理服务器"
          name="proxy"
          tooltip="HTTP/SOCKS5代理地址，如 http://127.0.0.1:7890"
        >
          <Input
            placeholder="如 http://127.0.0.1:7890"
            style={{ background: '#141414', borderColor: '#2a2a3e' }}
          />
        </Form.Item>

        <Form.Item>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={saving}
            onClick={handleSaveBrowser}
            style={{ borderRadius: 6, background: '#722ed1', borderColor: '#722ed1' }}
          >
            保存浏览器配置
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );

  return (
    <div>
      <Tabs
        type="card"
        items={[
          {
            key: 'ai',
            label: (
              <span>
                <RobotOutlined /> AI 配置
              </span>
            ),
            children: aiConfigContent,
          },
          {
            key: 'publish',
            label: (
              <span>
                <SendOutlined /> 发文策略
              </span>
            ),
            children: publishStrategyContent,
          },
          {
            key: 'browser',
            label: (
              <span>
                <ChromeOutlined /> 浏览器
              </span>
            ),
            children: browserConfigContent,
          },
        ]}
        style={{ marginTop: -8 }}
      />
    </div>
  );
};

export default Settings;
