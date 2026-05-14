Add-Type -AssemblyName System.Drawing

$Dir       = $PSScriptRoot
$IconPath  = Join-Path $Dir 'data-maker.ico'
$BatPath   = Join-Path $Dir 'launch-data-maker.bat'
$LinkName  = 'ARC-AGI-3 Data Maker.lnk'
$LinkPath  = Join-Path ([Environment]::GetFolderPath('Desktop')) $LinkName

# -- Draw 256x256 icon: 8x8 ARC-style pixel grid -------------
$size = 256
$bmp  = New-Object System.Drawing.Bitmap $size, $size
$g    = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = 'None'
$g.InterpolationMode = 'NearestNeighbor'
$g.PixelOffsetMode = 'Half'

# Solid black background
$bgBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 0, 0, 0))
$g.FillRectangle($bgBrush, 0, 0, $size, $size)
$bgBrush.Dispose()

# 8x8 grid, centered with margin
$gridSize = 8
$margin   = 16
$cellW    = [int](($size - 2 * $margin) / $gridSize)

# ARC palette indices used in pattern:
# 0 = black (background), 1 = blue, 2 = red, 3 = yellow, 4 = green, 5 = grey
$colors = @(
    [System.Drawing.Color]::FromArgb(255,  20,  20,  20),  # near-black (slight contrast vs bg)
    [System.Drawing.Color]::FromArgb(255,   0, 116, 217),  # blue   #0074D9
    [System.Drawing.Color]::FromArgb(255, 255,  65,  54),  # red    #FF4136
    [System.Drawing.Color]::FromArgb(255, 255, 220,   0),  # yellow #FFDC00
    [System.Drawing.Color]::FromArgb(255,  46, 204,  64),  # green  #2ECC40
    [System.Drawing.Color]::FromArgb(255, 170, 170, 170)   # grey   #AAAAAA
)

# Pattern evoking an ARC frame: blue player block, yellow goal, red obstacle, green path
$pattern = @(
    @(0,0,0,3,3,0,0,0),
    @(0,1,0,3,3,0,0,0),
    @(0,1,1,0,0,2,0,0),
    @(0,1,1,0,0,2,0,0),
    @(0,0,4,0,0,0,0,0),
    @(0,4,4,4,0,5,5,0),
    @(0,0,4,0,0,5,3,0),
    @(0,0,0,0,0,0,0,0)
)

for ($y = 0; $y -lt $gridSize; $y++) {
    for ($x = 0; $x -lt $gridSize; $x++) {
        $idx = $pattern[$y][$x]
        $brush = New-Object System.Drawing.SolidBrush $colors[$idx]
        $rx = $margin + $x * $cellW
        $ry = $margin + $y * $cellW
        $g.FillRectangle($brush, $rx, $ry, $cellW, $cellW)
        $brush.Dispose()
    }
}

# Thin separator lines for that pixel-grid look
$linePen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 50, 50, 50)), 1
for ($i = 0; $i -le $gridSize; $i++) {
    $p = $margin + $i * $cellW
    $g.DrawLine($linePen, $p, $margin, $p, $margin + $gridSize * $cellW)
    $g.DrawLine($linePen, $margin, $p, $margin + $gridSize * $cellW, $p)
}
$linePen.Dispose()

# Outer border for definition at small sizes
$borderPen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 0, 116, 217)), 6
$g.DrawRectangle($borderPen, 3, 3, $size - 7, $size - 7)
$borderPen.Dispose()

$g.Dispose()

# -- Wrap PNG into ICO (Vista+ PNG-in-ICO) -------------------
$ms  = New-Object System.IO.MemoryStream
$bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
$png = $ms.ToArray(); $ms.Close(); $bmp.Dispose()

if (Test-Path $IconPath) { Remove-Item $IconPath -Force }
$fs = New-Object System.IO.FileStream $IconPath, 'Create'
$bw = New-Object System.IO.BinaryWriter $fs
$bw.Write([uint16]0)        # reserved
$bw.Write([uint16]1)        # type 1 = icon
$bw.Write([uint16]1)        # 1 image
$bw.Write([byte]0)          # width (0 = 256)
$bw.Write([byte]0)          # height (0 = 256)
$bw.Write([byte]0)          # color count
$bw.Write([byte]0)          # reserved
$bw.Write([uint16]1)        # color planes
$bw.Write([uint16]32)       # bits per pixel
$bw.Write([uint32]$png.Length)
$bw.Write([uint32]22)       # offset to data
$bw.Write($png)
$bw.Close(); $fs.Close()

# -- Build .lnk on Desktop -----------------------------------
$ws  = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut($LinkPath)
$lnk.TargetPath       = $BatPath
$lnk.WorkingDirectory = $Dir
$lnk.IconLocation     = "$IconPath,0"
$lnk.Description      = 'ARC-AGI-3 Data Maker - view and label human replay recordings'
$lnk.WindowStyle      = 7
$lnk.Save()

Write-Host "[ok] Icon written to: $IconPath"
Write-Host "[ok] Shortcut placed on Desktop: $LinkName"
