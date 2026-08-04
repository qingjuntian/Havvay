package puzzle.dp;
import puzzle.Puzzle;

/**
 * Count the number of ways to decode a digit string where 1->A ... 26->Z.
 * LeetCode: Decode Ways
 * Approach: Right-to-left DP with a Fibonacci-style recurrence; special-cases '0'.
 * Complexity: Time O(n), Space O(1).
 * Created by qingjun on 2019/4/24.
 */
public class AlphabetParser implements Puzzle {

    int recur = 0;
    @Override
    public void resolve() {
        //String s = "1231212131221210212102121543542032324323244310444542332121212";
        String s = "1312212";
        long num = 0, num2 = 0;
        if (s != null && s.length() > 0) {
            //num = parseAlphabetFromHead(s, 0, s.length());
            //num = parseAlphabet(s, s.length());
            //num = parseAlphabetDp(s);
            num2 = parseAlphabetDp2(s.toCharArray(), 0, s.length() - 1);
            num = num2;
            if (num != num2) {
                System.out.println("something go wrong! " + num2);
            }
            //assert(num != num2);
        }
        System.out.println(String.format("str: %s; number: %d; recur: %d", s, num, recur));
    }

    private long parseAlphabetDp(String s) {
        if (s == null || s.length() <= 0) return 0;
        long a = 1;
        int index = s.length() - 1;
        long num = 1;
        int temp = -1;
        boolean zeroFlag = false;
        while (index >= 0) {
            char c = s.charAt(index);
            if (zeroFlag && c != '1' && c != '2') {
                return 0;
            }
            zeroFlag = c == '0';
            if (zeroFlag) {
                a = num;
                num = 0;
            }
            else if (temp > -1) {
                int alphabet = 10 * (c - '0') + temp;
                if (alphabet <= 26) {
                    long b = num;
                    num += a;
                    a  = b;
                } else {
                    a = num;
                }
            }
            temp = c - '0';
            index --;
        }
        return num;
    }

    private long parseAlphabetDp2(char[] chars, int l, int r) {
        if (l > r) return 0;
        boolean zeroFlag = false;
        for (int i = r; i >= l; i--) {
            if (zeroFlag ) {
                if (chars[i] == '1' || chars[i] == '2') {
                    //return leftPart * rightPart
                    if (i == r - 1) return parseAlphabetDp2(chars, l, r - 2);
                    if (i == l) return parseAlphabetDp2(chars, l + 2, r);
                    return parseAlphabetDp2(chars, l, i - 1) * parseAlphabetDp2(chars, i + 2, r);
                } else {
                    return 0;
                }
            }
            zeroFlag = chars[i] == '0';
        }

        if (zeroFlag) {
            // list start with zero
            return 0;
        }

        // There is no zero in the list now

        long a = 1;
        long num = 1;
        int temp = -1;
        while (r >= l) {
            char c = chars[r];
            if (temp > -1) {
                int alphabet = 10 * (c - '0') + temp;
                if (alphabet <= 26) {
                    long b = num;
                    num += a;
                    a  = b;
                } else {
                    a = num;
                }
            }
            temp = c - '0';
            r --;
        }
        return num;
    }

    private int parseAlphabetDp3(char[] chars, int n) {
        if (n <= 0) return 0;
        
        int prev2 = 1, prev1 = chars[0] != '0' ? 1 : 0;
        for (int i = 1; i < n; i++) {
            int current = 0;
            if (chars[i] != '0') {
                current += prev1;
            }
            int twoDigit = (chars[i - 1] - '0') * 10 + (chars[i] - '0');
            if (twoDigit >= 10 && twoDigit <= 26) {
                current += prev2;
            }
            prev2 = prev1;
            prev1 = current;
        }
        return prev1;
    }

    private int parseAlphabet(String s, int end) {
        recur++;
        int number = 0;
        if (end == 0) {
            number =  1;
        } else {
            if (isValid(s, end, 1)) {
                number += parseAlphabet(s, end - 1);
            }
            if (isValid(s, end, 2)) {
                number += parseAlphabet(s, end - 2);
            }
        }
        return number;
    }

    private boolean isValid(String s, int end, int i) {
        if ( i == 1 && s.charAt(end - 1)!= '0') return true;
        if (i == 2 && end >= 2) {
            int value = Integer.parseInt(s.substring(end - 2, end));
            if (value > 0 && value < 27) return true;
        }
        return false;
    }


    private int parseAlphabetFromHead(String s, int start, int length) {
        recur++;
        int number = 0;
        if (start ==  length) {
            number =  1;
        } else {
            if (isValidFromHead(s, start, 1)) {
                number += parseAlphabetFromHead(s, start + 1, length);
            }
            if (isValidFromHead(s, start, 2)) {
                number += parseAlphabetFromHead(s, start + 2, length);
            }
        }
        return number;
    }

    private boolean isValidFromHead(String s, int start, int i) {
        if ( i == 1 && s.charAt(start) != '0') return true;
        if (i == 2 && start + 2 <= s.length()) {
            int value = Integer.parseInt(s.substring(start, start + 2));
            if (value > 0 && value < 27) return true;
        }
        return false;
    }


}
