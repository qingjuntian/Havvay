package puzzle.concurrency;
import puzzle.Puzzle;

import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;

/**
 * Copy a file using Java NIO channels and a ByteBuffer.
 * NOTE: NIO file-copy demo (name is misleading -- not IP geolocation).
 */
public class IpLocPuzzle implements Puzzle {

    @Override
    public void resolve() {
        try {
            FileInputStream fin = new FileInputStream("JavaTest.iml");
            FileOutputStream fout = new FileOutputStream("JavaTest_cp.iml");

            FileChannel fcin = fin.getChannel();
            FileChannel fcout = fout.getChannel();

            ByteBuffer buffer = ByteBuffer.allocate( 100 );

            while (true) {
                buffer.clear();
                int r = fcin.read(buffer);
                if (r <= 0) break;

                buffer.flip();
                fcout.write(buffer);
            }

        } catch (Exception e) {

        }

    }

}
