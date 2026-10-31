import Modal from './Modal';
export default function ConfirmDialog({ open, title = 'Confirm action', message, onConfirm, onClose }) { return <Modal open={open} title={title} onClose={onClose}><p>{message}</p><button type="button" className="primary-button" onClick={onConfirm}>Confirm</button></Modal>; }
