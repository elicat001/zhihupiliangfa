import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Avatar,
  Button,
  Tag,
  Typography,
  Modal,
  Form,
  Input,
  InputNumber,
  Tabs,
  Spin,
  Popconfirm,
  Space,
  Switch,
  message,
  Empty,
  Badge,
  Alert,
  Tooltip,
} from 'antd';
import {
  UserOutlined,
  PlusOutlined,
  QrcodeOutlined,
  ImportOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
  DeleteOutlined,
  EditOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useAccountStore } from '../../stores/accountStore';
import { colors } from '../../styles/theme';
import type { Account, AccountLoginStatus } from '../../utils/types';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

/** 登录状态配置 */
const loginStatusConfig: Record<
  AccountLoginStatus,
  { color: string; text: string; icon: React.ReactNode }
> = {
  logged_in: {
    color: 'success',
    text: '已登录',
    icon: <CheckCircleOutlined />,
  },
  logged_out: {
    color: 'default',
    text: '未登录',
    icon: <CloseCircleOutlined />,
  },
  expired: {
    color: 'warning',
    text: '已过期',
    icon: <ExclamationCircleOutlined />,
  },
  checking: {
    color: 'processing',
    text: '检查中',
    icon: <SyncOutlined spin />,
  },
};

const AccountManage: React.FC = () => {
  const {
    accounts,
    loading,
    checkingIds,
    fetchAccounts,
    addAccount,
    deleteAccount,
    updateAccount,
    checkLogin,
    startQrcodeLogin,
    importCookie,
  } = useAccountStore();

  const [addModalVisible, setAddModalVisible] = useState(false);
  const [loginModalVisible, setLoginModalVisible] = useState(false);
  const [loginAccountId, setLoginAccountId] = useState<number | null>(null);
  const [qrcodeBase64, setQrcodeBase64] = useState<string | null>(null);
  const [qrcodeLoading, setQrcodeLoading] = useState(false);
  const [cookieInput, setCookieInput] = useState('');
  const [cookieLoading, setCookieLoading] = useState(false);
  const [qrStatus, setQrStatus] = useState<'idle' | 'waiting' | 'success' | 'timeout'>('idle');
  const [addForm] = Form.useForm();
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editAccount, setEditAccount] = useState<Account | null>(null);
  const [editForm] = Form.useForm();
  const pollTimerRef = React.useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetchAccounts();
    return () => {
      // 清理轮询定时器
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  /** 添加账号 */
  const handleAddAccount = async () => {
    try {
      const values = await addForm.validateFields();
      // 后端期望 { nickname, zhihu_uid?, cookie_data?, daily_limit? }
      await addAccount({
        nickname: values.nickname,
        zhihu_uid: values.zhihu_uid || '',
        daily_limit: values.daily_limit || 5,
      });
      message.success('账号添加成功');
      setAddModalVisible(false);
      addForm.resetFields();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error('添加账号失败');
    }
  };

  /** 检查登录态 */
  const handleCheckLogin = async (id: number) => {
    try {
      const isLoggedIn = await checkLogin(id);
      if (isLoggedIn) {
        message.success('账号登录状态正常');
      } else {
        message.warning('账号登录已失效，请重新登录');
      }
    } catch {
      message.error('检查登录态失败');
    }
  };

  /** 删除账号 */
  const handleDelete = async (id: number) => {
    try {
      await deleteAccount(id);
      message.success('账号已删除');
    } catch {
      message.error('删除失败');
    }
  };

  /** 打开编辑弹窗 */
  const handleOpenEdit = (account: Account) => {
    setEditAccount(account);
    editForm.setFieldsValue({
      nickname: account.nickname,
      daily_limit: account.daily_limit,
      is_active: account.is_active,
    });
    setEditModalVisible(true);
  };

  /** 保存编辑 */
  const handleSaveEdit = async () => {
    if (!editAccount) return;
    try {
      const values = await editForm.validateFields();
      await updateAccount(editAccount.id, {
        nickname: values.nickname,
        daily_limit: values.daily_limit,
        is_active: values.is_active,
      });
      message.success('账号信息已更新');
      setEditModalVisible(false);
      setEditAccount(null);
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error('更新失败');
    }
  };

  /** 打开登录弹窗 */
  const handleOpenLogin = (id: number) => {
    setLoginAccountId(id);
    setLoginModalVisible(true);
    setQrcodeBase64(null);
    setCookieInput('');
  };

  /** 停止轮询 */
  const stopPolling = () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  /** 扫码登录 */
  const handleQrcodeLogin = async () => {
    if (!loginAccountId) return;
    stopPolling();
    setQrcodeLoading(true);
    setQrStatus('idle');
    try {
      const qrcode = await startQrcodeLogin(loginAccountId);
      setQrcodeBase64(qrcode);
      setQrStatus('waiting');

      // 开始轮询检查登录状态（每3秒一次，最多120秒）
      let pollCount = 0;
      const maxPolls = 40; // 40 * 3s = 120s
      pollTimerRef.current = setInterval(async () => {
        pollCount++;
        if (pollCount > maxPolls) {
          stopPolling();
          setQrStatus('timeout');
          message.warning('扫码超时，请重新获取二维码');
          return;
        }
        try {
          const isLoggedIn = await checkLogin(loginAccountId);
          if (isLoggedIn) {
            stopPolling();
            setQrStatus('success');
            message.success('扫码登录成功！');
            // 延迟关闭弹窗，让用户看到成功状态
            setTimeout(() => {
              setLoginModalVisible(false);
              setQrcodeBase64(null);
              setQrStatus('idle');
              fetchAccounts();
            }, 1500);
          }
        } catch {
          // 检查失败不中断轮询
        }
      }, 3000);
    } catch {
      message.error('获取二维码失败');
    } finally {
      setQrcodeLoading(false);
    }
  };

  /** Cookie导入登录 */
  const handleCookieImport = async () => {
    if (!loginAccountId || !cookieInput.trim()) {
      message.warning('请输入Cookie');
      return;
    }
    setCookieLoading(true);
    try {
      await importCookie(loginAccountId, cookieInput.trim());
      message.success('Cookie导入成功');
      setLoginModalVisible(false);
      setCookieInput('');
    } catch {
      message.error('Cookie导入失败');
    } finally {
      setCookieLoading(false);
    }
  };

  /** 渲染账号卡片 */
  const renderAccountCard = (account: Account) => {
    const statusCfg = loginStatusConfig[account.login_status] || loginStatusConfig.logged_out;
    const isChecking = checkingIds.has(account.id);

    return (
      <Col xs={24} sm={12} lg={8} xl={6} key={account.id}>
        <Card
          style={{
            background: colors.bgContainer,
            borderColor: colors.border,
            borderRadius: 12,
            height: '100%',
          }}
          styles={{ body: { padding: 20 } }}
          hoverable
        >
          {/* 头部：头像和状态 */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              marginBottom: 16,
            }}
          >
            <Badge
              dot
              status={
                account.login_status === 'logged_in'
                  ? 'success'
                  : account.login_status === 'expired'
                  ? 'warning'
                  : 'default'
              }
              offset={[-4, 44]}
            >
              <Avatar
                size={52}
                icon={<UserOutlined />}
                style={{
                  background:
                    account.login_status === 'logged_in'
                      ? colors.primary
                      : '#434343',
                }}
              />
            </Badge>
            <div style={{ marginLeft: 12, flex: 1 }}>
              <Text
                strong
                style={{
                  color: colors.textPrimary,
                  fontSize: 15,
                  display: 'block',
                }}
              >
                {account.nickname || '未命名'}
              </Text>
              <Tooltip
                title={`上次检查: ${account.created_at ? new Date(account.created_at).toLocaleString('zh-CN') : '暂无记录'}`}
                placement="right"
              >
                <Tag
                  icon={isChecking ? <SyncOutlined spin /> : statusCfg.icon}
                  color={isChecking ? 'processing' : statusCfg.color}
                  style={{ marginTop: 4, cursor: 'pointer' }}
                >
                  {isChecking ? '检查中...' : statusCfg.text}
                </Tag>
              </Tooltip>
            </div>
          </div>

          {/* 详情信息 */}
          <div style={{ marginBottom: 16 }}>
            {account.zhihu_uid && (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginBottom: 6,
                }}
              >
                <Text style={{ color: colors.textTertiary, fontSize: 13 }}>知乎UID</Text>
                <Text style={{ color: colors.textSecondary, fontSize: 13 }}>
                  {account.zhihu_uid}
                </Text>
              </div>
            )}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: 6,
              }}
            >
              <Text style={{ color: colors.textTertiary, fontSize: 13 }}>每日上限</Text>
              <Text style={{ color: colors.textSecondary, fontSize: 13 }}>
                {account.daily_limit} 篇
              </Text>
            </div>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: 6,
              }}
            >
              <Text style={{ color: colors.textTertiary, fontSize: 13 }}>启用状态</Text>
              <Text
                style={{
                  color: account.is_active ? colors.success : colors.error,
                  fontSize: 13,
                }}
              >
                {account.is_active ? '已启用' : '已禁用'}
              </Text>
            </div>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: 6,
              }}
            >
              <Text style={{ color: colors.textTertiary, fontSize: 13 }}>创建时间</Text>
              <Text style={{ color: colors.textSecondary, fontSize: 13 }}>
                {new Date(account.created_at).toLocaleString('zh-CN')}
              </Text>
            </div>
          </div>

          {/* 操作按钮 */}
          <Space size="small" wrap>
            <Button
              size="small"
              type="primary"
              icon={<ReloadOutlined />}
              loading={isChecking}
              onClick={() => handleCheckLogin(account.id)}
            >
              检查登录态
            </Button>
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleOpenEdit(account)}
            >
              编辑
            </Button>
            <Button
              size="small"
              icon={<QrcodeOutlined />}
              onClick={() => handleOpenLogin(account.id)}
            >
              登录
            </Button>
            <Popconfirm
              title="确认删除此账号？"
              onConfirm={() => handleDelete(account.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button size="small" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          </Space>
        </Card>
      </Col>
    );
  };

  // Account health: detect unhealthy accounts
  const unhealthyAccounts = accounts.filter(
    (a) => a.login_status === 'expired' || a.login_status === 'logged_out'
  );
  const expiredAccounts = accounts.filter((a) => a.login_status === 'expired');
  const loggedOutAccounts = accounts.filter((a) => a.login_status === 'logged_out');

  return (
    <div>
      {/* Account Health Alert Banner */}
      {unhealthyAccounts.length > 0 && (
        <Alert
          type="error"
          showIcon
          closable
          style={{
            marginBottom: 16,
            background: 'rgba(255, 77, 79, 0.08)',
            border: '1px solid rgba(255, 77, 79, 0.3)',
            borderRadius: 8,
          }}
          message={
            <span style={{ color: colors.error }}>
              账号健康预警
            </span>
          }
          description={
            <span style={{ color: colors.textSecondary }}>
              {expiredAccounts.length > 0 && (
                <span>
                  {expiredAccounts.length} 个账号登录已过期
                  ({expiredAccounts.map((a) => a.nickname || '未命名').join('、')})
                </span>
              )}
              {expiredAccounts.length > 0 && loggedOutAccounts.length > 0 && '；'}
              {loggedOutAccounts.length > 0 && (
                <span>
                  {loggedOutAccounts.length} 个账号未登录
                  ({loggedOutAccounts.map((a) => a.nickname || '未命名').join('、')})
                </span>
              )}
              。请及时处理以确保发布任务正常执行。
            </span>
          }
        />
      )}

      {/* 顶部操作栏 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <Text style={{ color: colors.textSecondary }}>
          共 {accounts.length} 个账号，
          {accounts.filter((a) => a.login_status === 'logged_in').length} 个在线
        </Text>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setAddModalVisible(true)}
          style={{ borderRadius: 6 }}
        >
          添加账号
        </Button>
      </div>

      {/* 账号卡片列表 */}
      {loading && accounts.length === 0 ? (
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            paddingTop: 100,
          }}
        >
          <Spin size="large" tip="加载中..." />
        </div>
      ) : accounts.length === 0 ? (
        <Card
          style={{
            background: colors.bgContainer,
            borderColor: colors.border,
            borderRadius: 12,
          }}
        >
          <Empty description="暂无账号，请点击右上角添加" />
        </Card>
      ) : (
        <Row gutter={[16, 16]}>{accounts.map(renderAccountCard)}</Row>
      )}

      {/* 添加账号弹窗 */}
      <Modal
        title="添加知乎账号"
        open={addModalVisible}
        onOk={handleAddAccount}
        onCancel={() => {
          setAddModalVisible(false);
          addForm.resetFields();
        }}
        okText="添加"
        cancelText="取消"
        confirmLoading={loading}
      >
        <Form form={addForm} layout="vertical" className="enhanced-form" style={{ marginTop: 16 }}>
          <Form.Item
            label="昵称"
            name="nickname"
            rules={[{ required: true, message: '请输入账号昵称' }]}
          >
            <Input placeholder="请输入账号昵称，方便识别" />
          </Form.Item>
          <Form.Item label="知乎UID" name="zhihu_uid">
            <Input placeholder="可选，知乎用户ID" />
          </Form.Item>
          <Form.Item label="每日发布上限" name="daily_limit" initialValue={5}>
            <Input type="number" min={1} max={50} placeholder="每日最大发布篇数" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑账号弹窗 */}
      <Modal
        title="编辑账号"
        open={editModalVisible}
        onOk={handleSaveEdit}
        onCancel={() => {
          setEditModalVisible(false);
          setEditAccount(null);
        }}
        okText="保存"
        cancelText="取消"
        confirmLoading={loading}
      >
        <Form form={editForm} layout="vertical" className="enhanced-form" style={{ marginTop: 16 }}>
          <Form.Item
            label="昵称"
            name="nickname"
            rules={[{ required: true, message: '请输入昵称' }]}
          >
            <Input placeholder="账号昵称" />
          </Form.Item>
          <Form.Item
            label="每日发布上限"
            name="daily_limit"
          >
            <InputNumber min={1} max={50} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            label="启用状态"
            name="is_active"
            valuePropName="checked"
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 登录弹窗 */}
      <Modal
        title="账号登录"
        open={loginModalVisible}
        onCancel={() => {
          stopPolling();
          setLoginModalVisible(false);
          setQrcodeBase64(null);
          setCookieInput('');
          setQrStatus('idle');
        }}
        footer={null}
        width={500}
      >
        <Tabs
          items={[
            {
              key: 'cookie',
              label: (
                <span>
                  <ImportOutlined /> Cookie 导入
                </span>
              ),
              children: (
                <div>
                  <Paragraph style={{ color: colors.textSecondary, marginBottom: 16 }}>
                    请从浏览器开发者工具中复制知乎的Cookie，粘贴到下方输入框。
                  </Paragraph>
                  <TextArea
                    rows={6}
                    placeholder="粘贴Cookie内容..."
                    value={cookieInput}
                    onChange={(e) => setCookieInput(e.target.value)}
                    style={{
                      background: colors.bgInput,
                      borderColor: colors.border,
                      marginBottom: 16,
                      fontFamily: 'monospace',
                      fontSize: 12,
                    }}
                  />
                  <Button
                    type="primary"
                    block
                    loading={cookieLoading}
                    onClick={handleCookieImport}
                    icon={<ImportOutlined />}
                  >
                    导入 Cookie
                  </Button>
                </div>
              ),
            },
            {
              key: 'qrcode',
              label: (
                <span>
                  <QrcodeOutlined /> 扫码登录
                </span>
              ),
              children: (
                <div style={{ textAlign: 'center', padding: '16px 0' }}>
                  <Paragraph style={{ color: colors.textSecondary, marginBottom: 16 }}>
                    点击下方按钮获取二维码，使用知乎App扫码登录。
                  </Paragraph>

                  {/* 二维码显示区域 */}
                  <div
                    style={{
                      width: 240,
                      height: 240,
                      margin: '0 auto 16px',
                      background: '#fff',
                      borderRadius: 12,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      overflow: 'hidden',
                    }}
                  >
                    {qrcodeLoading ? (
                      <Spin size="large" tip="加载中..." />
                    ) : qrcodeBase64 ? (
                      <img
                        src={
                          qrcodeBase64.startsWith('data:')
                            ? qrcodeBase64
                            : `data:image/png;base64,${qrcodeBase64}`
                        }
                        alt="登录二维码"
                        style={{
                          width: '100%',
                          height: '100%',
                          objectFit: 'contain',
                        }}
                      />
                    ) : (
                      <div style={{ color: '#999', textAlign: 'center' }}>
                        <QrcodeOutlined
                          style={{ fontSize: 48, display: 'block', marginBottom: 8 }}
                        />
                        <span>点击下方按钮获取二维码</span>
                      </div>
                    )}
                  </div>

                  {/* 扫码状态提示 */}
                  {qrStatus === 'waiting' && (
                    <div style={{ marginBottom: 12 }}>
                      <Tag icon={<SyncOutlined spin />} color="processing">
                        等待扫码中...请使用知乎APP扫描
                      </Tag>
                    </div>
                  )}
                  {qrStatus === 'success' && (
                    <div style={{ marginBottom: 12 }}>
                      <Tag icon={<CheckCircleOutlined />} color="success">
                        扫码登录成功！
                      </Tag>
                    </div>
                  )}
                  {qrStatus === 'timeout' && (
                    <div style={{ marginBottom: 12 }}>
                      <Tag icon={<ExclamationCircleOutlined />} color="warning">
                        二维码已过期，请重新获取
                      </Tag>
                    </div>
                  )}

                  <Button
                    type="primary"
                    icon={<QrcodeOutlined />}
                    onClick={handleQrcodeLogin}
                    loading={qrcodeLoading}
                  >
                    {qrcodeBase64 ? '刷新二维码' : '获取二维码'}
                  </Button>
                </div>
              ),
            },
          ]}
        />
      </Modal>
    </div>
  );
};

export default AccountManage;
