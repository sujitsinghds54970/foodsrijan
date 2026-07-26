import AccountsModule from '../accounts/AccountsModule'

interface AccountsProps {
  branchId?: number
}

export default function Accounts({ branchId }: AccountsProps) {
  return <AccountsModule branchId={branchId} />
}
