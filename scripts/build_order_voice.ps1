Add-Type -AssemblyName System.Speech
$audioDirectory = Join-Path $PSScriptRoot '../frontend/admin/src/assets/audio'
New-Item -ItemType Directory -Force -Path $audioDirectory | Out-Null
$voiceFiles = @(
  @{ Name='new-order-zh.wav'; Voice='Microsoft Huihui Desktop'; Text='您有新的订单，请及时查看' },
  @{ Name='order-voice-enabled-zh.wav'; Voice='Microsoft Huihui Desktop'; Text='订单语音提醒已开启' },
  @{ Name='new-order-en.wav'; Voice='Microsoft Zira Desktop'; Text='You have a new order. Please check it.' },
  @{ Name='order-voice-enabled-en.wav'; Voice='Microsoft Zira Desktop'; Text='Order voice alerts are enabled.' }
)
foreach ($voiceFile in $voiceFiles) {
  $speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
  try {
    $speaker.SelectVoice($voiceFile.Voice)
    $speaker.Volume = 100
    $speaker.Rate = 0
    $speaker.SetOutputToWaveFile((Join-Path $audioDirectory $voiceFile.Name))
    $speaker.Speak($voiceFile.Text)
  } finally { $speaker.Dispose() }
}
