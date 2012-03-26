XSIZE=$1                                                                                                                                                                             
XSIZE=$1

if [ "$MAXSIZE" != "" -a "$MAXSIZE" == "${MAXSIZE//[^0-9]/}" ]
then
        echo "Default length is $MAXSIZE"
else
        MAXSIZE=8
        echo "Default length is $MAXSIZE"
fi

CHAR_ARRAY=(
q w e r t y u i o p a s d f g h j k l z x c v b n m Q W E R T Y U I O P A S D
F G H J K L Z X C V B N M 1 2 3 4 5 6 7 8 9 0 ! @ # $ % ^ & * ( )
)

MODNUM=${#CHAR_ARRAY[*]}

PWD_LEN=0

while [ $PWD_LEN -lt $MAXSIZE ]
do
  X=$(($RANDOM%500))
  Y=0
  while [ $Y -lt $X ]
  do
    ((Y++))
    INDEX=$(($RANDOM%$MODNUM))
  done
  echo -n "${CHAR_ARRAY[$INDEX]}"
  ((PWD_LEN++))
done

echo ""

exit 0
