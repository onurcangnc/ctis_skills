set -euo pipefail
export LC_ALL=C
tr '[:upper:]' '[:lower:]' < "ctis166/input.txt" |
  tr -cs '[:alnum:]' '\n' |
  sed '/^$/d' |
  sort -u
