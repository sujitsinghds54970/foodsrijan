import Joyride, { CallBackProps, STATUS, Step } from 'react-joyride'

type Props = {
  run: boolean
  steps: Step[]
  onFinish: () => void
}

export default function DoctorOnboardingTour({ run, steps, onFinish }: Props) {
  const handleCallback = (data: CallBackProps) => {
    const { status } = data
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      onFinish()
    }
  }

  return (
    <Joyride
      run={run}
      steps={steps}
      continuous
      showSkipButton
      showProgress
      disableOverlayClose
      callback={handleCallback}
      styles={{
        options: {
          primaryColor: '#0f766e',
          zIndex: 10000,
        },
      }}
    />
  )
}
