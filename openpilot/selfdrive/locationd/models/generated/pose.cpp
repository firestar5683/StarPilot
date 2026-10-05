#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_6249615963109186962) {
   out_6249615963109186962[0] = delta_x[0] + nom_x[0];
   out_6249615963109186962[1] = delta_x[1] + nom_x[1];
   out_6249615963109186962[2] = delta_x[2] + nom_x[2];
   out_6249615963109186962[3] = delta_x[3] + nom_x[3];
   out_6249615963109186962[4] = delta_x[4] + nom_x[4];
   out_6249615963109186962[5] = delta_x[5] + nom_x[5];
   out_6249615963109186962[6] = delta_x[6] + nom_x[6];
   out_6249615963109186962[7] = delta_x[7] + nom_x[7];
   out_6249615963109186962[8] = delta_x[8] + nom_x[8];
   out_6249615963109186962[9] = delta_x[9] + nom_x[9];
   out_6249615963109186962[10] = delta_x[10] + nom_x[10];
   out_6249615963109186962[11] = delta_x[11] + nom_x[11];
   out_6249615963109186962[12] = delta_x[12] + nom_x[12];
   out_6249615963109186962[13] = delta_x[13] + nom_x[13];
   out_6249615963109186962[14] = delta_x[14] + nom_x[14];
   out_6249615963109186962[15] = delta_x[15] + nom_x[15];
   out_6249615963109186962[16] = delta_x[16] + nom_x[16];
   out_6249615963109186962[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_7563571606094106109) {
   out_7563571606094106109[0] = -nom_x[0] + true_x[0];
   out_7563571606094106109[1] = -nom_x[1] + true_x[1];
   out_7563571606094106109[2] = -nom_x[2] + true_x[2];
   out_7563571606094106109[3] = -nom_x[3] + true_x[3];
   out_7563571606094106109[4] = -nom_x[4] + true_x[4];
   out_7563571606094106109[5] = -nom_x[5] + true_x[5];
   out_7563571606094106109[6] = -nom_x[6] + true_x[6];
   out_7563571606094106109[7] = -nom_x[7] + true_x[7];
   out_7563571606094106109[8] = -nom_x[8] + true_x[8];
   out_7563571606094106109[9] = -nom_x[9] + true_x[9];
   out_7563571606094106109[10] = -nom_x[10] + true_x[10];
   out_7563571606094106109[11] = -nom_x[11] + true_x[11];
   out_7563571606094106109[12] = -nom_x[12] + true_x[12];
   out_7563571606094106109[13] = -nom_x[13] + true_x[13];
   out_7563571606094106109[14] = -nom_x[14] + true_x[14];
   out_7563571606094106109[15] = -nom_x[15] + true_x[15];
   out_7563571606094106109[16] = -nom_x[16] + true_x[16];
   out_7563571606094106109[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_3216188353717940043) {
   out_3216188353717940043[0] = 1.0;
   out_3216188353717940043[1] = 0.0;
   out_3216188353717940043[2] = 0.0;
   out_3216188353717940043[3] = 0.0;
   out_3216188353717940043[4] = 0.0;
   out_3216188353717940043[5] = 0.0;
   out_3216188353717940043[6] = 0.0;
   out_3216188353717940043[7] = 0.0;
   out_3216188353717940043[8] = 0.0;
   out_3216188353717940043[9] = 0.0;
   out_3216188353717940043[10] = 0.0;
   out_3216188353717940043[11] = 0.0;
   out_3216188353717940043[12] = 0.0;
   out_3216188353717940043[13] = 0.0;
   out_3216188353717940043[14] = 0.0;
   out_3216188353717940043[15] = 0.0;
   out_3216188353717940043[16] = 0.0;
   out_3216188353717940043[17] = 0.0;
   out_3216188353717940043[18] = 0.0;
   out_3216188353717940043[19] = 1.0;
   out_3216188353717940043[20] = 0.0;
   out_3216188353717940043[21] = 0.0;
   out_3216188353717940043[22] = 0.0;
   out_3216188353717940043[23] = 0.0;
   out_3216188353717940043[24] = 0.0;
   out_3216188353717940043[25] = 0.0;
   out_3216188353717940043[26] = 0.0;
   out_3216188353717940043[27] = 0.0;
   out_3216188353717940043[28] = 0.0;
   out_3216188353717940043[29] = 0.0;
   out_3216188353717940043[30] = 0.0;
   out_3216188353717940043[31] = 0.0;
   out_3216188353717940043[32] = 0.0;
   out_3216188353717940043[33] = 0.0;
   out_3216188353717940043[34] = 0.0;
   out_3216188353717940043[35] = 0.0;
   out_3216188353717940043[36] = 0.0;
   out_3216188353717940043[37] = 0.0;
   out_3216188353717940043[38] = 1.0;
   out_3216188353717940043[39] = 0.0;
   out_3216188353717940043[40] = 0.0;
   out_3216188353717940043[41] = 0.0;
   out_3216188353717940043[42] = 0.0;
   out_3216188353717940043[43] = 0.0;
   out_3216188353717940043[44] = 0.0;
   out_3216188353717940043[45] = 0.0;
   out_3216188353717940043[46] = 0.0;
   out_3216188353717940043[47] = 0.0;
   out_3216188353717940043[48] = 0.0;
   out_3216188353717940043[49] = 0.0;
   out_3216188353717940043[50] = 0.0;
   out_3216188353717940043[51] = 0.0;
   out_3216188353717940043[52] = 0.0;
   out_3216188353717940043[53] = 0.0;
   out_3216188353717940043[54] = 0.0;
   out_3216188353717940043[55] = 0.0;
   out_3216188353717940043[56] = 0.0;
   out_3216188353717940043[57] = 1.0;
   out_3216188353717940043[58] = 0.0;
   out_3216188353717940043[59] = 0.0;
   out_3216188353717940043[60] = 0.0;
   out_3216188353717940043[61] = 0.0;
   out_3216188353717940043[62] = 0.0;
   out_3216188353717940043[63] = 0.0;
   out_3216188353717940043[64] = 0.0;
   out_3216188353717940043[65] = 0.0;
   out_3216188353717940043[66] = 0.0;
   out_3216188353717940043[67] = 0.0;
   out_3216188353717940043[68] = 0.0;
   out_3216188353717940043[69] = 0.0;
   out_3216188353717940043[70] = 0.0;
   out_3216188353717940043[71] = 0.0;
   out_3216188353717940043[72] = 0.0;
   out_3216188353717940043[73] = 0.0;
   out_3216188353717940043[74] = 0.0;
   out_3216188353717940043[75] = 0.0;
   out_3216188353717940043[76] = 1.0;
   out_3216188353717940043[77] = 0.0;
   out_3216188353717940043[78] = 0.0;
   out_3216188353717940043[79] = 0.0;
   out_3216188353717940043[80] = 0.0;
   out_3216188353717940043[81] = 0.0;
   out_3216188353717940043[82] = 0.0;
   out_3216188353717940043[83] = 0.0;
   out_3216188353717940043[84] = 0.0;
   out_3216188353717940043[85] = 0.0;
   out_3216188353717940043[86] = 0.0;
   out_3216188353717940043[87] = 0.0;
   out_3216188353717940043[88] = 0.0;
   out_3216188353717940043[89] = 0.0;
   out_3216188353717940043[90] = 0.0;
   out_3216188353717940043[91] = 0.0;
   out_3216188353717940043[92] = 0.0;
   out_3216188353717940043[93] = 0.0;
   out_3216188353717940043[94] = 0.0;
   out_3216188353717940043[95] = 1.0;
   out_3216188353717940043[96] = 0.0;
   out_3216188353717940043[97] = 0.0;
   out_3216188353717940043[98] = 0.0;
   out_3216188353717940043[99] = 0.0;
   out_3216188353717940043[100] = 0.0;
   out_3216188353717940043[101] = 0.0;
   out_3216188353717940043[102] = 0.0;
   out_3216188353717940043[103] = 0.0;
   out_3216188353717940043[104] = 0.0;
   out_3216188353717940043[105] = 0.0;
   out_3216188353717940043[106] = 0.0;
   out_3216188353717940043[107] = 0.0;
   out_3216188353717940043[108] = 0.0;
   out_3216188353717940043[109] = 0.0;
   out_3216188353717940043[110] = 0.0;
   out_3216188353717940043[111] = 0.0;
   out_3216188353717940043[112] = 0.0;
   out_3216188353717940043[113] = 0.0;
   out_3216188353717940043[114] = 1.0;
   out_3216188353717940043[115] = 0.0;
   out_3216188353717940043[116] = 0.0;
   out_3216188353717940043[117] = 0.0;
   out_3216188353717940043[118] = 0.0;
   out_3216188353717940043[119] = 0.0;
   out_3216188353717940043[120] = 0.0;
   out_3216188353717940043[121] = 0.0;
   out_3216188353717940043[122] = 0.0;
   out_3216188353717940043[123] = 0.0;
   out_3216188353717940043[124] = 0.0;
   out_3216188353717940043[125] = 0.0;
   out_3216188353717940043[126] = 0.0;
   out_3216188353717940043[127] = 0.0;
   out_3216188353717940043[128] = 0.0;
   out_3216188353717940043[129] = 0.0;
   out_3216188353717940043[130] = 0.0;
   out_3216188353717940043[131] = 0.0;
   out_3216188353717940043[132] = 0.0;
   out_3216188353717940043[133] = 1.0;
   out_3216188353717940043[134] = 0.0;
   out_3216188353717940043[135] = 0.0;
   out_3216188353717940043[136] = 0.0;
   out_3216188353717940043[137] = 0.0;
   out_3216188353717940043[138] = 0.0;
   out_3216188353717940043[139] = 0.0;
   out_3216188353717940043[140] = 0.0;
   out_3216188353717940043[141] = 0.0;
   out_3216188353717940043[142] = 0.0;
   out_3216188353717940043[143] = 0.0;
   out_3216188353717940043[144] = 0.0;
   out_3216188353717940043[145] = 0.0;
   out_3216188353717940043[146] = 0.0;
   out_3216188353717940043[147] = 0.0;
   out_3216188353717940043[148] = 0.0;
   out_3216188353717940043[149] = 0.0;
   out_3216188353717940043[150] = 0.0;
   out_3216188353717940043[151] = 0.0;
   out_3216188353717940043[152] = 1.0;
   out_3216188353717940043[153] = 0.0;
   out_3216188353717940043[154] = 0.0;
   out_3216188353717940043[155] = 0.0;
   out_3216188353717940043[156] = 0.0;
   out_3216188353717940043[157] = 0.0;
   out_3216188353717940043[158] = 0.0;
   out_3216188353717940043[159] = 0.0;
   out_3216188353717940043[160] = 0.0;
   out_3216188353717940043[161] = 0.0;
   out_3216188353717940043[162] = 0.0;
   out_3216188353717940043[163] = 0.0;
   out_3216188353717940043[164] = 0.0;
   out_3216188353717940043[165] = 0.0;
   out_3216188353717940043[166] = 0.0;
   out_3216188353717940043[167] = 0.0;
   out_3216188353717940043[168] = 0.0;
   out_3216188353717940043[169] = 0.0;
   out_3216188353717940043[170] = 0.0;
   out_3216188353717940043[171] = 1.0;
   out_3216188353717940043[172] = 0.0;
   out_3216188353717940043[173] = 0.0;
   out_3216188353717940043[174] = 0.0;
   out_3216188353717940043[175] = 0.0;
   out_3216188353717940043[176] = 0.0;
   out_3216188353717940043[177] = 0.0;
   out_3216188353717940043[178] = 0.0;
   out_3216188353717940043[179] = 0.0;
   out_3216188353717940043[180] = 0.0;
   out_3216188353717940043[181] = 0.0;
   out_3216188353717940043[182] = 0.0;
   out_3216188353717940043[183] = 0.0;
   out_3216188353717940043[184] = 0.0;
   out_3216188353717940043[185] = 0.0;
   out_3216188353717940043[186] = 0.0;
   out_3216188353717940043[187] = 0.0;
   out_3216188353717940043[188] = 0.0;
   out_3216188353717940043[189] = 0.0;
   out_3216188353717940043[190] = 1.0;
   out_3216188353717940043[191] = 0.0;
   out_3216188353717940043[192] = 0.0;
   out_3216188353717940043[193] = 0.0;
   out_3216188353717940043[194] = 0.0;
   out_3216188353717940043[195] = 0.0;
   out_3216188353717940043[196] = 0.0;
   out_3216188353717940043[197] = 0.0;
   out_3216188353717940043[198] = 0.0;
   out_3216188353717940043[199] = 0.0;
   out_3216188353717940043[200] = 0.0;
   out_3216188353717940043[201] = 0.0;
   out_3216188353717940043[202] = 0.0;
   out_3216188353717940043[203] = 0.0;
   out_3216188353717940043[204] = 0.0;
   out_3216188353717940043[205] = 0.0;
   out_3216188353717940043[206] = 0.0;
   out_3216188353717940043[207] = 0.0;
   out_3216188353717940043[208] = 0.0;
   out_3216188353717940043[209] = 1.0;
   out_3216188353717940043[210] = 0.0;
   out_3216188353717940043[211] = 0.0;
   out_3216188353717940043[212] = 0.0;
   out_3216188353717940043[213] = 0.0;
   out_3216188353717940043[214] = 0.0;
   out_3216188353717940043[215] = 0.0;
   out_3216188353717940043[216] = 0.0;
   out_3216188353717940043[217] = 0.0;
   out_3216188353717940043[218] = 0.0;
   out_3216188353717940043[219] = 0.0;
   out_3216188353717940043[220] = 0.0;
   out_3216188353717940043[221] = 0.0;
   out_3216188353717940043[222] = 0.0;
   out_3216188353717940043[223] = 0.0;
   out_3216188353717940043[224] = 0.0;
   out_3216188353717940043[225] = 0.0;
   out_3216188353717940043[226] = 0.0;
   out_3216188353717940043[227] = 0.0;
   out_3216188353717940043[228] = 1.0;
   out_3216188353717940043[229] = 0.0;
   out_3216188353717940043[230] = 0.0;
   out_3216188353717940043[231] = 0.0;
   out_3216188353717940043[232] = 0.0;
   out_3216188353717940043[233] = 0.0;
   out_3216188353717940043[234] = 0.0;
   out_3216188353717940043[235] = 0.0;
   out_3216188353717940043[236] = 0.0;
   out_3216188353717940043[237] = 0.0;
   out_3216188353717940043[238] = 0.0;
   out_3216188353717940043[239] = 0.0;
   out_3216188353717940043[240] = 0.0;
   out_3216188353717940043[241] = 0.0;
   out_3216188353717940043[242] = 0.0;
   out_3216188353717940043[243] = 0.0;
   out_3216188353717940043[244] = 0.0;
   out_3216188353717940043[245] = 0.0;
   out_3216188353717940043[246] = 0.0;
   out_3216188353717940043[247] = 1.0;
   out_3216188353717940043[248] = 0.0;
   out_3216188353717940043[249] = 0.0;
   out_3216188353717940043[250] = 0.0;
   out_3216188353717940043[251] = 0.0;
   out_3216188353717940043[252] = 0.0;
   out_3216188353717940043[253] = 0.0;
   out_3216188353717940043[254] = 0.0;
   out_3216188353717940043[255] = 0.0;
   out_3216188353717940043[256] = 0.0;
   out_3216188353717940043[257] = 0.0;
   out_3216188353717940043[258] = 0.0;
   out_3216188353717940043[259] = 0.0;
   out_3216188353717940043[260] = 0.0;
   out_3216188353717940043[261] = 0.0;
   out_3216188353717940043[262] = 0.0;
   out_3216188353717940043[263] = 0.0;
   out_3216188353717940043[264] = 0.0;
   out_3216188353717940043[265] = 0.0;
   out_3216188353717940043[266] = 1.0;
   out_3216188353717940043[267] = 0.0;
   out_3216188353717940043[268] = 0.0;
   out_3216188353717940043[269] = 0.0;
   out_3216188353717940043[270] = 0.0;
   out_3216188353717940043[271] = 0.0;
   out_3216188353717940043[272] = 0.0;
   out_3216188353717940043[273] = 0.0;
   out_3216188353717940043[274] = 0.0;
   out_3216188353717940043[275] = 0.0;
   out_3216188353717940043[276] = 0.0;
   out_3216188353717940043[277] = 0.0;
   out_3216188353717940043[278] = 0.0;
   out_3216188353717940043[279] = 0.0;
   out_3216188353717940043[280] = 0.0;
   out_3216188353717940043[281] = 0.0;
   out_3216188353717940043[282] = 0.0;
   out_3216188353717940043[283] = 0.0;
   out_3216188353717940043[284] = 0.0;
   out_3216188353717940043[285] = 1.0;
   out_3216188353717940043[286] = 0.0;
   out_3216188353717940043[287] = 0.0;
   out_3216188353717940043[288] = 0.0;
   out_3216188353717940043[289] = 0.0;
   out_3216188353717940043[290] = 0.0;
   out_3216188353717940043[291] = 0.0;
   out_3216188353717940043[292] = 0.0;
   out_3216188353717940043[293] = 0.0;
   out_3216188353717940043[294] = 0.0;
   out_3216188353717940043[295] = 0.0;
   out_3216188353717940043[296] = 0.0;
   out_3216188353717940043[297] = 0.0;
   out_3216188353717940043[298] = 0.0;
   out_3216188353717940043[299] = 0.0;
   out_3216188353717940043[300] = 0.0;
   out_3216188353717940043[301] = 0.0;
   out_3216188353717940043[302] = 0.0;
   out_3216188353717940043[303] = 0.0;
   out_3216188353717940043[304] = 1.0;
   out_3216188353717940043[305] = 0.0;
   out_3216188353717940043[306] = 0.0;
   out_3216188353717940043[307] = 0.0;
   out_3216188353717940043[308] = 0.0;
   out_3216188353717940043[309] = 0.0;
   out_3216188353717940043[310] = 0.0;
   out_3216188353717940043[311] = 0.0;
   out_3216188353717940043[312] = 0.0;
   out_3216188353717940043[313] = 0.0;
   out_3216188353717940043[314] = 0.0;
   out_3216188353717940043[315] = 0.0;
   out_3216188353717940043[316] = 0.0;
   out_3216188353717940043[317] = 0.0;
   out_3216188353717940043[318] = 0.0;
   out_3216188353717940043[319] = 0.0;
   out_3216188353717940043[320] = 0.0;
   out_3216188353717940043[321] = 0.0;
   out_3216188353717940043[322] = 0.0;
   out_3216188353717940043[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_6979270288524198339) {
   out_6979270288524198339[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_6979270288524198339[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_6979270288524198339[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_6979270288524198339[3] = dt*state[12] + state[3];
   out_6979270288524198339[4] = dt*state[13] + state[4];
   out_6979270288524198339[5] = dt*state[14] + state[5];
   out_6979270288524198339[6] = state[6];
   out_6979270288524198339[7] = state[7];
   out_6979270288524198339[8] = state[8];
   out_6979270288524198339[9] = state[9];
   out_6979270288524198339[10] = state[10];
   out_6979270288524198339[11] = state[11];
   out_6979270288524198339[12] = state[12];
   out_6979270288524198339[13] = state[13];
   out_6979270288524198339[14] = state[14];
   out_6979270288524198339[15] = state[15];
   out_6979270288524198339[16] = state[16];
   out_6979270288524198339[17] = state[17];
}
void F_fun(double *state, double dt, double *out_6492284477154870567) {
   out_6492284477154870567[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6492284477154870567[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6492284477154870567[2] = 0;
   out_6492284477154870567[3] = 0;
   out_6492284477154870567[4] = 0;
   out_6492284477154870567[5] = 0;
   out_6492284477154870567[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6492284477154870567[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6492284477154870567[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6492284477154870567[9] = 0;
   out_6492284477154870567[10] = 0;
   out_6492284477154870567[11] = 0;
   out_6492284477154870567[12] = 0;
   out_6492284477154870567[13] = 0;
   out_6492284477154870567[14] = 0;
   out_6492284477154870567[15] = 0;
   out_6492284477154870567[16] = 0;
   out_6492284477154870567[17] = 0;
   out_6492284477154870567[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6492284477154870567[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6492284477154870567[20] = 0;
   out_6492284477154870567[21] = 0;
   out_6492284477154870567[22] = 0;
   out_6492284477154870567[23] = 0;
   out_6492284477154870567[24] = 0;
   out_6492284477154870567[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6492284477154870567[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6492284477154870567[27] = 0;
   out_6492284477154870567[28] = 0;
   out_6492284477154870567[29] = 0;
   out_6492284477154870567[30] = 0;
   out_6492284477154870567[31] = 0;
   out_6492284477154870567[32] = 0;
   out_6492284477154870567[33] = 0;
   out_6492284477154870567[34] = 0;
   out_6492284477154870567[35] = 0;
   out_6492284477154870567[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6492284477154870567[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6492284477154870567[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6492284477154870567[39] = 0;
   out_6492284477154870567[40] = 0;
   out_6492284477154870567[41] = 0;
   out_6492284477154870567[42] = 0;
   out_6492284477154870567[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6492284477154870567[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6492284477154870567[45] = 0;
   out_6492284477154870567[46] = 0;
   out_6492284477154870567[47] = 0;
   out_6492284477154870567[48] = 0;
   out_6492284477154870567[49] = 0;
   out_6492284477154870567[50] = 0;
   out_6492284477154870567[51] = 0;
   out_6492284477154870567[52] = 0;
   out_6492284477154870567[53] = 0;
   out_6492284477154870567[54] = 0;
   out_6492284477154870567[55] = 0;
   out_6492284477154870567[56] = 0;
   out_6492284477154870567[57] = 1;
   out_6492284477154870567[58] = 0;
   out_6492284477154870567[59] = 0;
   out_6492284477154870567[60] = 0;
   out_6492284477154870567[61] = 0;
   out_6492284477154870567[62] = 0;
   out_6492284477154870567[63] = 0;
   out_6492284477154870567[64] = 0;
   out_6492284477154870567[65] = 0;
   out_6492284477154870567[66] = dt;
   out_6492284477154870567[67] = 0;
   out_6492284477154870567[68] = 0;
   out_6492284477154870567[69] = 0;
   out_6492284477154870567[70] = 0;
   out_6492284477154870567[71] = 0;
   out_6492284477154870567[72] = 0;
   out_6492284477154870567[73] = 0;
   out_6492284477154870567[74] = 0;
   out_6492284477154870567[75] = 0;
   out_6492284477154870567[76] = 1;
   out_6492284477154870567[77] = 0;
   out_6492284477154870567[78] = 0;
   out_6492284477154870567[79] = 0;
   out_6492284477154870567[80] = 0;
   out_6492284477154870567[81] = 0;
   out_6492284477154870567[82] = 0;
   out_6492284477154870567[83] = 0;
   out_6492284477154870567[84] = 0;
   out_6492284477154870567[85] = dt;
   out_6492284477154870567[86] = 0;
   out_6492284477154870567[87] = 0;
   out_6492284477154870567[88] = 0;
   out_6492284477154870567[89] = 0;
   out_6492284477154870567[90] = 0;
   out_6492284477154870567[91] = 0;
   out_6492284477154870567[92] = 0;
   out_6492284477154870567[93] = 0;
   out_6492284477154870567[94] = 0;
   out_6492284477154870567[95] = 1;
   out_6492284477154870567[96] = 0;
   out_6492284477154870567[97] = 0;
   out_6492284477154870567[98] = 0;
   out_6492284477154870567[99] = 0;
   out_6492284477154870567[100] = 0;
   out_6492284477154870567[101] = 0;
   out_6492284477154870567[102] = 0;
   out_6492284477154870567[103] = 0;
   out_6492284477154870567[104] = dt;
   out_6492284477154870567[105] = 0;
   out_6492284477154870567[106] = 0;
   out_6492284477154870567[107] = 0;
   out_6492284477154870567[108] = 0;
   out_6492284477154870567[109] = 0;
   out_6492284477154870567[110] = 0;
   out_6492284477154870567[111] = 0;
   out_6492284477154870567[112] = 0;
   out_6492284477154870567[113] = 0;
   out_6492284477154870567[114] = 1;
   out_6492284477154870567[115] = 0;
   out_6492284477154870567[116] = 0;
   out_6492284477154870567[117] = 0;
   out_6492284477154870567[118] = 0;
   out_6492284477154870567[119] = 0;
   out_6492284477154870567[120] = 0;
   out_6492284477154870567[121] = 0;
   out_6492284477154870567[122] = 0;
   out_6492284477154870567[123] = 0;
   out_6492284477154870567[124] = 0;
   out_6492284477154870567[125] = 0;
   out_6492284477154870567[126] = 0;
   out_6492284477154870567[127] = 0;
   out_6492284477154870567[128] = 0;
   out_6492284477154870567[129] = 0;
   out_6492284477154870567[130] = 0;
   out_6492284477154870567[131] = 0;
   out_6492284477154870567[132] = 0;
   out_6492284477154870567[133] = 1;
   out_6492284477154870567[134] = 0;
   out_6492284477154870567[135] = 0;
   out_6492284477154870567[136] = 0;
   out_6492284477154870567[137] = 0;
   out_6492284477154870567[138] = 0;
   out_6492284477154870567[139] = 0;
   out_6492284477154870567[140] = 0;
   out_6492284477154870567[141] = 0;
   out_6492284477154870567[142] = 0;
   out_6492284477154870567[143] = 0;
   out_6492284477154870567[144] = 0;
   out_6492284477154870567[145] = 0;
   out_6492284477154870567[146] = 0;
   out_6492284477154870567[147] = 0;
   out_6492284477154870567[148] = 0;
   out_6492284477154870567[149] = 0;
   out_6492284477154870567[150] = 0;
   out_6492284477154870567[151] = 0;
   out_6492284477154870567[152] = 1;
   out_6492284477154870567[153] = 0;
   out_6492284477154870567[154] = 0;
   out_6492284477154870567[155] = 0;
   out_6492284477154870567[156] = 0;
   out_6492284477154870567[157] = 0;
   out_6492284477154870567[158] = 0;
   out_6492284477154870567[159] = 0;
   out_6492284477154870567[160] = 0;
   out_6492284477154870567[161] = 0;
   out_6492284477154870567[162] = 0;
   out_6492284477154870567[163] = 0;
   out_6492284477154870567[164] = 0;
   out_6492284477154870567[165] = 0;
   out_6492284477154870567[166] = 0;
   out_6492284477154870567[167] = 0;
   out_6492284477154870567[168] = 0;
   out_6492284477154870567[169] = 0;
   out_6492284477154870567[170] = 0;
   out_6492284477154870567[171] = 1;
   out_6492284477154870567[172] = 0;
   out_6492284477154870567[173] = 0;
   out_6492284477154870567[174] = 0;
   out_6492284477154870567[175] = 0;
   out_6492284477154870567[176] = 0;
   out_6492284477154870567[177] = 0;
   out_6492284477154870567[178] = 0;
   out_6492284477154870567[179] = 0;
   out_6492284477154870567[180] = 0;
   out_6492284477154870567[181] = 0;
   out_6492284477154870567[182] = 0;
   out_6492284477154870567[183] = 0;
   out_6492284477154870567[184] = 0;
   out_6492284477154870567[185] = 0;
   out_6492284477154870567[186] = 0;
   out_6492284477154870567[187] = 0;
   out_6492284477154870567[188] = 0;
   out_6492284477154870567[189] = 0;
   out_6492284477154870567[190] = 1;
   out_6492284477154870567[191] = 0;
   out_6492284477154870567[192] = 0;
   out_6492284477154870567[193] = 0;
   out_6492284477154870567[194] = 0;
   out_6492284477154870567[195] = 0;
   out_6492284477154870567[196] = 0;
   out_6492284477154870567[197] = 0;
   out_6492284477154870567[198] = 0;
   out_6492284477154870567[199] = 0;
   out_6492284477154870567[200] = 0;
   out_6492284477154870567[201] = 0;
   out_6492284477154870567[202] = 0;
   out_6492284477154870567[203] = 0;
   out_6492284477154870567[204] = 0;
   out_6492284477154870567[205] = 0;
   out_6492284477154870567[206] = 0;
   out_6492284477154870567[207] = 0;
   out_6492284477154870567[208] = 0;
   out_6492284477154870567[209] = 1;
   out_6492284477154870567[210] = 0;
   out_6492284477154870567[211] = 0;
   out_6492284477154870567[212] = 0;
   out_6492284477154870567[213] = 0;
   out_6492284477154870567[214] = 0;
   out_6492284477154870567[215] = 0;
   out_6492284477154870567[216] = 0;
   out_6492284477154870567[217] = 0;
   out_6492284477154870567[218] = 0;
   out_6492284477154870567[219] = 0;
   out_6492284477154870567[220] = 0;
   out_6492284477154870567[221] = 0;
   out_6492284477154870567[222] = 0;
   out_6492284477154870567[223] = 0;
   out_6492284477154870567[224] = 0;
   out_6492284477154870567[225] = 0;
   out_6492284477154870567[226] = 0;
   out_6492284477154870567[227] = 0;
   out_6492284477154870567[228] = 1;
   out_6492284477154870567[229] = 0;
   out_6492284477154870567[230] = 0;
   out_6492284477154870567[231] = 0;
   out_6492284477154870567[232] = 0;
   out_6492284477154870567[233] = 0;
   out_6492284477154870567[234] = 0;
   out_6492284477154870567[235] = 0;
   out_6492284477154870567[236] = 0;
   out_6492284477154870567[237] = 0;
   out_6492284477154870567[238] = 0;
   out_6492284477154870567[239] = 0;
   out_6492284477154870567[240] = 0;
   out_6492284477154870567[241] = 0;
   out_6492284477154870567[242] = 0;
   out_6492284477154870567[243] = 0;
   out_6492284477154870567[244] = 0;
   out_6492284477154870567[245] = 0;
   out_6492284477154870567[246] = 0;
   out_6492284477154870567[247] = 1;
   out_6492284477154870567[248] = 0;
   out_6492284477154870567[249] = 0;
   out_6492284477154870567[250] = 0;
   out_6492284477154870567[251] = 0;
   out_6492284477154870567[252] = 0;
   out_6492284477154870567[253] = 0;
   out_6492284477154870567[254] = 0;
   out_6492284477154870567[255] = 0;
   out_6492284477154870567[256] = 0;
   out_6492284477154870567[257] = 0;
   out_6492284477154870567[258] = 0;
   out_6492284477154870567[259] = 0;
   out_6492284477154870567[260] = 0;
   out_6492284477154870567[261] = 0;
   out_6492284477154870567[262] = 0;
   out_6492284477154870567[263] = 0;
   out_6492284477154870567[264] = 0;
   out_6492284477154870567[265] = 0;
   out_6492284477154870567[266] = 1;
   out_6492284477154870567[267] = 0;
   out_6492284477154870567[268] = 0;
   out_6492284477154870567[269] = 0;
   out_6492284477154870567[270] = 0;
   out_6492284477154870567[271] = 0;
   out_6492284477154870567[272] = 0;
   out_6492284477154870567[273] = 0;
   out_6492284477154870567[274] = 0;
   out_6492284477154870567[275] = 0;
   out_6492284477154870567[276] = 0;
   out_6492284477154870567[277] = 0;
   out_6492284477154870567[278] = 0;
   out_6492284477154870567[279] = 0;
   out_6492284477154870567[280] = 0;
   out_6492284477154870567[281] = 0;
   out_6492284477154870567[282] = 0;
   out_6492284477154870567[283] = 0;
   out_6492284477154870567[284] = 0;
   out_6492284477154870567[285] = 1;
   out_6492284477154870567[286] = 0;
   out_6492284477154870567[287] = 0;
   out_6492284477154870567[288] = 0;
   out_6492284477154870567[289] = 0;
   out_6492284477154870567[290] = 0;
   out_6492284477154870567[291] = 0;
   out_6492284477154870567[292] = 0;
   out_6492284477154870567[293] = 0;
   out_6492284477154870567[294] = 0;
   out_6492284477154870567[295] = 0;
   out_6492284477154870567[296] = 0;
   out_6492284477154870567[297] = 0;
   out_6492284477154870567[298] = 0;
   out_6492284477154870567[299] = 0;
   out_6492284477154870567[300] = 0;
   out_6492284477154870567[301] = 0;
   out_6492284477154870567[302] = 0;
   out_6492284477154870567[303] = 0;
   out_6492284477154870567[304] = 1;
   out_6492284477154870567[305] = 0;
   out_6492284477154870567[306] = 0;
   out_6492284477154870567[307] = 0;
   out_6492284477154870567[308] = 0;
   out_6492284477154870567[309] = 0;
   out_6492284477154870567[310] = 0;
   out_6492284477154870567[311] = 0;
   out_6492284477154870567[312] = 0;
   out_6492284477154870567[313] = 0;
   out_6492284477154870567[314] = 0;
   out_6492284477154870567[315] = 0;
   out_6492284477154870567[316] = 0;
   out_6492284477154870567[317] = 0;
   out_6492284477154870567[318] = 0;
   out_6492284477154870567[319] = 0;
   out_6492284477154870567[320] = 0;
   out_6492284477154870567[321] = 0;
   out_6492284477154870567[322] = 0;
   out_6492284477154870567[323] = 1;
}
void h_4(double *state, double *unused, double *out_9173610292480735262) {
   out_9173610292480735262[0] = state[6] + state[9];
   out_9173610292480735262[1] = state[7] + state[10];
   out_9173610292480735262[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_6987995563561847615) {
   out_6987995563561847615[0] = 0;
   out_6987995563561847615[1] = 0;
   out_6987995563561847615[2] = 0;
   out_6987995563561847615[3] = 0;
   out_6987995563561847615[4] = 0;
   out_6987995563561847615[5] = 0;
   out_6987995563561847615[6] = 1;
   out_6987995563561847615[7] = 0;
   out_6987995563561847615[8] = 0;
   out_6987995563561847615[9] = 1;
   out_6987995563561847615[10] = 0;
   out_6987995563561847615[11] = 0;
   out_6987995563561847615[12] = 0;
   out_6987995563561847615[13] = 0;
   out_6987995563561847615[14] = 0;
   out_6987995563561847615[15] = 0;
   out_6987995563561847615[16] = 0;
   out_6987995563561847615[17] = 0;
   out_6987995563561847615[18] = 0;
   out_6987995563561847615[19] = 0;
   out_6987995563561847615[20] = 0;
   out_6987995563561847615[21] = 0;
   out_6987995563561847615[22] = 0;
   out_6987995563561847615[23] = 0;
   out_6987995563561847615[24] = 0;
   out_6987995563561847615[25] = 1;
   out_6987995563561847615[26] = 0;
   out_6987995563561847615[27] = 0;
   out_6987995563561847615[28] = 1;
   out_6987995563561847615[29] = 0;
   out_6987995563561847615[30] = 0;
   out_6987995563561847615[31] = 0;
   out_6987995563561847615[32] = 0;
   out_6987995563561847615[33] = 0;
   out_6987995563561847615[34] = 0;
   out_6987995563561847615[35] = 0;
   out_6987995563561847615[36] = 0;
   out_6987995563561847615[37] = 0;
   out_6987995563561847615[38] = 0;
   out_6987995563561847615[39] = 0;
   out_6987995563561847615[40] = 0;
   out_6987995563561847615[41] = 0;
   out_6987995563561847615[42] = 0;
   out_6987995563561847615[43] = 0;
   out_6987995563561847615[44] = 1;
   out_6987995563561847615[45] = 0;
   out_6987995563561847615[46] = 0;
   out_6987995563561847615[47] = 1;
   out_6987995563561847615[48] = 0;
   out_6987995563561847615[49] = 0;
   out_6987995563561847615[50] = 0;
   out_6987995563561847615[51] = 0;
   out_6987995563561847615[52] = 0;
   out_6987995563561847615[53] = 0;
}
void h_10(double *state, double *unused, double *out_4580681428320651947) {
   out_4580681428320651947[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_4580681428320651947[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_4580681428320651947[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_4215236079406633816) {
   out_4215236079406633816[0] = 0;
   out_4215236079406633816[1] = 9.8100000000000005*cos(state[1]);
   out_4215236079406633816[2] = 0;
   out_4215236079406633816[3] = 0;
   out_4215236079406633816[4] = -state[8];
   out_4215236079406633816[5] = state[7];
   out_4215236079406633816[6] = 0;
   out_4215236079406633816[7] = state[5];
   out_4215236079406633816[8] = -state[4];
   out_4215236079406633816[9] = 0;
   out_4215236079406633816[10] = 0;
   out_4215236079406633816[11] = 0;
   out_4215236079406633816[12] = 1;
   out_4215236079406633816[13] = 0;
   out_4215236079406633816[14] = 0;
   out_4215236079406633816[15] = 1;
   out_4215236079406633816[16] = 0;
   out_4215236079406633816[17] = 0;
   out_4215236079406633816[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_4215236079406633816[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_4215236079406633816[20] = 0;
   out_4215236079406633816[21] = state[8];
   out_4215236079406633816[22] = 0;
   out_4215236079406633816[23] = -state[6];
   out_4215236079406633816[24] = -state[5];
   out_4215236079406633816[25] = 0;
   out_4215236079406633816[26] = state[3];
   out_4215236079406633816[27] = 0;
   out_4215236079406633816[28] = 0;
   out_4215236079406633816[29] = 0;
   out_4215236079406633816[30] = 0;
   out_4215236079406633816[31] = 1;
   out_4215236079406633816[32] = 0;
   out_4215236079406633816[33] = 0;
   out_4215236079406633816[34] = 1;
   out_4215236079406633816[35] = 0;
   out_4215236079406633816[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_4215236079406633816[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_4215236079406633816[38] = 0;
   out_4215236079406633816[39] = -state[7];
   out_4215236079406633816[40] = state[6];
   out_4215236079406633816[41] = 0;
   out_4215236079406633816[42] = state[4];
   out_4215236079406633816[43] = -state[3];
   out_4215236079406633816[44] = 0;
   out_4215236079406633816[45] = 0;
   out_4215236079406633816[46] = 0;
   out_4215236079406633816[47] = 0;
   out_4215236079406633816[48] = 0;
   out_4215236079406633816[49] = 0;
   out_4215236079406633816[50] = 1;
   out_4215236079406633816[51] = 0;
   out_4215236079406633816[52] = 0;
   out_4215236079406633816[53] = 1;
}
void h_13(double *state, double *unused, double *out_7612834127399631628) {
   out_7612834127399631628[0] = state[3];
   out_7612834127399631628[1] = state[4];
   out_7612834127399631628[2] = state[5];
}
void H_13(double *state, double *unused, double *out_3848117301831003072) {
   out_3848117301831003072[0] = 0;
   out_3848117301831003072[1] = 0;
   out_3848117301831003072[2] = 0;
   out_3848117301831003072[3] = 1;
   out_3848117301831003072[4] = 0;
   out_3848117301831003072[5] = 0;
   out_3848117301831003072[6] = 0;
   out_3848117301831003072[7] = 0;
   out_3848117301831003072[8] = 0;
   out_3848117301831003072[9] = 0;
   out_3848117301831003072[10] = 0;
   out_3848117301831003072[11] = 0;
   out_3848117301831003072[12] = 0;
   out_3848117301831003072[13] = 0;
   out_3848117301831003072[14] = 0;
   out_3848117301831003072[15] = 0;
   out_3848117301831003072[16] = 0;
   out_3848117301831003072[17] = 0;
   out_3848117301831003072[18] = 0;
   out_3848117301831003072[19] = 0;
   out_3848117301831003072[20] = 0;
   out_3848117301831003072[21] = 0;
   out_3848117301831003072[22] = 1;
   out_3848117301831003072[23] = 0;
   out_3848117301831003072[24] = 0;
   out_3848117301831003072[25] = 0;
   out_3848117301831003072[26] = 0;
   out_3848117301831003072[27] = 0;
   out_3848117301831003072[28] = 0;
   out_3848117301831003072[29] = 0;
   out_3848117301831003072[30] = 0;
   out_3848117301831003072[31] = 0;
   out_3848117301831003072[32] = 0;
   out_3848117301831003072[33] = 0;
   out_3848117301831003072[34] = 0;
   out_3848117301831003072[35] = 0;
   out_3848117301831003072[36] = 0;
   out_3848117301831003072[37] = 0;
   out_3848117301831003072[38] = 0;
   out_3848117301831003072[39] = 0;
   out_3848117301831003072[40] = 0;
   out_3848117301831003072[41] = 1;
   out_3848117301831003072[42] = 0;
   out_3848117301831003072[43] = 0;
   out_3848117301831003072[44] = 0;
   out_3848117301831003072[45] = 0;
   out_3848117301831003072[46] = 0;
   out_3848117301831003072[47] = 0;
   out_3848117301831003072[48] = 0;
   out_3848117301831003072[49] = 0;
   out_3848117301831003072[50] = 0;
   out_3848117301831003072[51] = 0;
   out_3848117301831003072[52] = 0;
   out_3848117301831003072[53] = 0;
}
void h_14(double *state, double *unused, double *out_6844612447345845382) {
   out_6844612447345845382[0] = state[6];
   out_6844612447345845382[1] = state[7];
   out_6844612447345845382[2] = state[8];
}
void H_14(double *state, double *unused, double *out_3905207131266475319) {
   out_3905207131266475319[0] = 0;
   out_3905207131266475319[1] = 0;
   out_3905207131266475319[2] = 0;
   out_3905207131266475319[3] = 0;
   out_3905207131266475319[4] = 0;
   out_3905207131266475319[5] = 0;
   out_3905207131266475319[6] = 1;
   out_3905207131266475319[7] = 0;
   out_3905207131266475319[8] = 0;
   out_3905207131266475319[9] = 0;
   out_3905207131266475319[10] = 0;
   out_3905207131266475319[11] = 0;
   out_3905207131266475319[12] = 0;
   out_3905207131266475319[13] = 0;
   out_3905207131266475319[14] = 0;
   out_3905207131266475319[15] = 0;
   out_3905207131266475319[16] = 0;
   out_3905207131266475319[17] = 0;
   out_3905207131266475319[18] = 0;
   out_3905207131266475319[19] = 0;
   out_3905207131266475319[20] = 0;
   out_3905207131266475319[21] = 0;
   out_3905207131266475319[22] = 0;
   out_3905207131266475319[23] = 0;
   out_3905207131266475319[24] = 0;
   out_3905207131266475319[25] = 1;
   out_3905207131266475319[26] = 0;
   out_3905207131266475319[27] = 0;
   out_3905207131266475319[28] = 0;
   out_3905207131266475319[29] = 0;
   out_3905207131266475319[30] = 0;
   out_3905207131266475319[31] = 0;
   out_3905207131266475319[32] = 0;
   out_3905207131266475319[33] = 0;
   out_3905207131266475319[34] = 0;
   out_3905207131266475319[35] = 0;
   out_3905207131266475319[36] = 0;
   out_3905207131266475319[37] = 0;
   out_3905207131266475319[38] = 0;
   out_3905207131266475319[39] = 0;
   out_3905207131266475319[40] = 0;
   out_3905207131266475319[41] = 0;
   out_3905207131266475319[42] = 0;
   out_3905207131266475319[43] = 0;
   out_3905207131266475319[44] = 1;
   out_3905207131266475319[45] = 0;
   out_3905207131266475319[46] = 0;
   out_3905207131266475319[47] = 0;
   out_3905207131266475319[48] = 0;
   out_3905207131266475319[49] = 0;
   out_3905207131266475319[50] = 0;
   out_3905207131266475319[51] = 0;
   out_3905207131266475319[52] = 0;
   out_3905207131266475319[53] = 0;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_6249615963109186962) {
  err_fun(nom_x, delta_x, out_6249615963109186962);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7563571606094106109) {
  inv_err_fun(nom_x, true_x, out_7563571606094106109);
}
void pose_H_mod_fun(double *state, double *out_3216188353717940043) {
  H_mod_fun(state, out_3216188353717940043);
}
void pose_f_fun(double *state, double dt, double *out_6979270288524198339) {
  f_fun(state,  dt, out_6979270288524198339);
}
void pose_F_fun(double *state, double dt, double *out_6492284477154870567) {
  F_fun(state,  dt, out_6492284477154870567);
}
void pose_h_4(double *state, double *unused, double *out_9173610292480735262) {
  h_4(state, unused, out_9173610292480735262);
}
void pose_H_4(double *state, double *unused, double *out_6987995563561847615) {
  H_4(state, unused, out_6987995563561847615);
}
void pose_h_10(double *state, double *unused, double *out_4580681428320651947) {
  h_10(state, unused, out_4580681428320651947);
}
void pose_H_10(double *state, double *unused, double *out_4215236079406633816) {
  H_10(state, unused, out_4215236079406633816);
}
void pose_h_13(double *state, double *unused, double *out_7612834127399631628) {
  h_13(state, unused, out_7612834127399631628);
}
void pose_H_13(double *state, double *unused, double *out_3848117301831003072) {
  H_13(state, unused, out_3848117301831003072);
}
void pose_h_14(double *state, double *unused, double *out_6844612447345845382) {
  h_14(state, unused, out_6844612447345845382);
}
void pose_H_14(double *state, double *unused, double *out_3905207131266475319) {
  H_14(state, unused, out_3905207131266475319);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)
