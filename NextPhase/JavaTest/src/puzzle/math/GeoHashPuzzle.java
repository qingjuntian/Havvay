package puzzle.math;
import puzzle.Puzzle;

/**
 * Encode a (latitude, longitude) pair into a geohash string.
 * Approach: Repeatedly bisect the lat/lon ranges, interleave the bits, and emit base-32 characters.
 * Complexity: Time O(precision), Space O(1).
 * Created by qingjuntian on 7/18/16.
 */
public class GeoHashPuzzle implements Puzzle {
    private static final char[] BASE32 = {};

    @Override
    public void resolve() {
        int[] arr = new int[] {1, 2, 3, 4, 5, 6};
    }

    static void encode_geohash(double latitude, double longitude, int precision, char[] geohash) {
        boolean is_even=true;
        int i=0;
        double[] lat = new double[2];
        double[] lon = new double[2];
        double mid;
        char bits[] = {16,8,4,2,1};
        int bit=0, ch=0;
        lat[0] = -90.0; lat[1] = 90.0;
        lon[0] = -180.0; lon[1] = 180.0;
        while (i < precision) {
            if (is_even) {
                mid = (lon[0] + lon[1]) / 2;
                if (longitude > mid) {
                    ch |= bits[bit];
                    lon[0] = mid;
                } else
                    lon[1] = mid;
            } else {
                mid = (lat[0] + lat[1]) / 2;
                if (latitude > mid) {
                    ch |= bits[bit];
                    lat[0] = mid;
                } else
                    lat[1] = mid;
            }
            is_even = !is_even;
            if (bit < 4)
                bit++;
            else {
                geohash[i++] = BASE32[ch];
                bit = 0;
                ch = 0;
            }
        }
        geohash[i] = 0;
    }
}
