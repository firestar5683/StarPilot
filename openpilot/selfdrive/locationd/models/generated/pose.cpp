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
void err_fun(double *nom_x, double *delta_x, double *out_3094993718265680010) {
   out_3094993718265680010[0] = delta_x[0] + nom_x[0];
   out_3094993718265680010[1] = delta_x[1] + nom_x[1];
   out_3094993718265680010[2] = delta_x[2] + nom_x[2];
   out_3094993718265680010[3] = delta_x[3] + nom_x[3];
   out_3094993718265680010[4] = delta_x[4] + nom_x[4];
   out_3094993718265680010[5] = delta_x[5] + nom_x[5];
   out_3094993718265680010[6] = delta_x[6] + nom_x[6];
   out_3094993718265680010[7] = delta_x[7] + nom_x[7];
   out_3094993718265680010[8] = delta_x[8] + nom_x[8];
   out_3094993718265680010[9] = delta_x[9] + nom_x[9];
   out_3094993718265680010[10] = delta_x[10] + nom_x[10];
   out_3094993718265680010[11] = delta_x[11] + nom_x[11];
   out_3094993718265680010[12] = delta_x[12] + nom_x[12];
   out_3094993718265680010[13] = delta_x[13] + nom_x[13];
   out_3094993718265680010[14] = delta_x[14] + nom_x[14];
   out_3094993718265680010[15] = delta_x[15] + nom_x[15];
   out_3094993718265680010[16] = delta_x[16] + nom_x[16];
   out_3094993718265680010[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_446507105452282601) {
   out_446507105452282601[0] = -nom_x[0] + true_x[0];
   out_446507105452282601[1] = -nom_x[1] + true_x[1];
   out_446507105452282601[2] = -nom_x[2] + true_x[2];
   out_446507105452282601[3] = -nom_x[3] + true_x[3];
   out_446507105452282601[4] = -nom_x[4] + true_x[4];
   out_446507105452282601[5] = -nom_x[5] + true_x[5];
   out_446507105452282601[6] = -nom_x[6] + true_x[6];
   out_446507105452282601[7] = -nom_x[7] + true_x[7];
   out_446507105452282601[8] = -nom_x[8] + true_x[8];
   out_446507105452282601[9] = -nom_x[9] + true_x[9];
   out_446507105452282601[10] = -nom_x[10] + true_x[10];
   out_446507105452282601[11] = -nom_x[11] + true_x[11];
   out_446507105452282601[12] = -nom_x[12] + true_x[12];
   out_446507105452282601[13] = -nom_x[13] + true_x[13];
   out_446507105452282601[14] = -nom_x[14] + true_x[14];
   out_446507105452282601[15] = -nom_x[15] + true_x[15];
   out_446507105452282601[16] = -nom_x[16] + true_x[16];
   out_446507105452282601[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_96002479082188485) {
   out_96002479082188485[0] = 1.0;
   out_96002479082188485[1] = 0.0;
   out_96002479082188485[2] = 0.0;
   out_96002479082188485[3] = 0.0;
   out_96002479082188485[4] = 0.0;
   out_96002479082188485[5] = 0.0;
   out_96002479082188485[6] = 0.0;
   out_96002479082188485[7] = 0.0;
   out_96002479082188485[8] = 0.0;
   out_96002479082188485[9] = 0.0;
   out_96002479082188485[10] = 0.0;
   out_96002479082188485[11] = 0.0;
   out_96002479082188485[12] = 0.0;
   out_96002479082188485[13] = 0.0;
   out_96002479082188485[14] = 0.0;
   out_96002479082188485[15] = 0.0;
   out_96002479082188485[16] = 0.0;
   out_96002479082188485[17] = 0.0;
   out_96002479082188485[18] = 0.0;
   out_96002479082188485[19] = 1.0;
   out_96002479082188485[20] = 0.0;
   out_96002479082188485[21] = 0.0;
   out_96002479082188485[22] = 0.0;
   out_96002479082188485[23] = 0.0;
   out_96002479082188485[24] = 0.0;
   out_96002479082188485[25] = 0.0;
   out_96002479082188485[26] = 0.0;
   out_96002479082188485[27] = 0.0;
   out_96002479082188485[28] = 0.0;
   out_96002479082188485[29] = 0.0;
   out_96002479082188485[30] = 0.0;
   out_96002479082188485[31] = 0.0;
   out_96002479082188485[32] = 0.0;
   out_96002479082188485[33] = 0.0;
   out_96002479082188485[34] = 0.0;
   out_96002479082188485[35] = 0.0;
   out_96002479082188485[36] = 0.0;
   out_96002479082188485[37] = 0.0;
   out_96002479082188485[38] = 1.0;
   out_96002479082188485[39] = 0.0;
   out_96002479082188485[40] = 0.0;
   out_96002479082188485[41] = 0.0;
   out_96002479082188485[42] = 0.0;
   out_96002479082188485[43] = 0.0;
   out_96002479082188485[44] = 0.0;
   out_96002479082188485[45] = 0.0;
   out_96002479082188485[46] = 0.0;
   out_96002479082188485[47] = 0.0;
   out_96002479082188485[48] = 0.0;
   out_96002479082188485[49] = 0.0;
   out_96002479082188485[50] = 0.0;
   out_96002479082188485[51] = 0.0;
   out_96002479082188485[52] = 0.0;
   out_96002479082188485[53] = 0.0;
   out_96002479082188485[54] = 0.0;
   out_96002479082188485[55] = 0.0;
   out_96002479082188485[56] = 0.0;
   out_96002479082188485[57] = 1.0;
   out_96002479082188485[58] = 0.0;
   out_96002479082188485[59] = 0.0;
   out_96002479082188485[60] = 0.0;
   out_96002479082188485[61] = 0.0;
   out_96002479082188485[62] = 0.0;
   out_96002479082188485[63] = 0.0;
   out_96002479082188485[64] = 0.0;
   out_96002479082188485[65] = 0.0;
   out_96002479082188485[66] = 0.0;
   out_96002479082188485[67] = 0.0;
   out_96002479082188485[68] = 0.0;
   out_96002479082188485[69] = 0.0;
   out_96002479082188485[70] = 0.0;
   out_96002479082188485[71] = 0.0;
   out_96002479082188485[72] = 0.0;
   out_96002479082188485[73] = 0.0;
   out_96002479082188485[74] = 0.0;
   out_96002479082188485[75] = 0.0;
   out_96002479082188485[76] = 1.0;
   out_96002479082188485[77] = 0.0;
   out_96002479082188485[78] = 0.0;
   out_96002479082188485[79] = 0.0;
   out_96002479082188485[80] = 0.0;
   out_96002479082188485[81] = 0.0;
   out_96002479082188485[82] = 0.0;
   out_96002479082188485[83] = 0.0;
   out_96002479082188485[84] = 0.0;
   out_96002479082188485[85] = 0.0;
   out_96002479082188485[86] = 0.0;
   out_96002479082188485[87] = 0.0;
   out_96002479082188485[88] = 0.0;
   out_96002479082188485[89] = 0.0;
   out_96002479082188485[90] = 0.0;
   out_96002479082188485[91] = 0.0;
   out_96002479082188485[92] = 0.0;
   out_96002479082188485[93] = 0.0;
   out_96002479082188485[94] = 0.0;
   out_96002479082188485[95] = 1.0;
   out_96002479082188485[96] = 0.0;
   out_96002479082188485[97] = 0.0;
   out_96002479082188485[98] = 0.0;
   out_96002479082188485[99] = 0.0;
   out_96002479082188485[100] = 0.0;
   out_96002479082188485[101] = 0.0;
   out_96002479082188485[102] = 0.0;
   out_96002479082188485[103] = 0.0;
   out_96002479082188485[104] = 0.0;
   out_96002479082188485[105] = 0.0;
   out_96002479082188485[106] = 0.0;
   out_96002479082188485[107] = 0.0;
   out_96002479082188485[108] = 0.0;
   out_96002479082188485[109] = 0.0;
   out_96002479082188485[110] = 0.0;
   out_96002479082188485[111] = 0.0;
   out_96002479082188485[112] = 0.0;
   out_96002479082188485[113] = 0.0;
   out_96002479082188485[114] = 1.0;
   out_96002479082188485[115] = 0.0;
   out_96002479082188485[116] = 0.0;
   out_96002479082188485[117] = 0.0;
   out_96002479082188485[118] = 0.0;
   out_96002479082188485[119] = 0.0;
   out_96002479082188485[120] = 0.0;
   out_96002479082188485[121] = 0.0;
   out_96002479082188485[122] = 0.0;
   out_96002479082188485[123] = 0.0;
   out_96002479082188485[124] = 0.0;
   out_96002479082188485[125] = 0.0;
   out_96002479082188485[126] = 0.0;
   out_96002479082188485[127] = 0.0;
   out_96002479082188485[128] = 0.0;
   out_96002479082188485[129] = 0.0;
   out_96002479082188485[130] = 0.0;
   out_96002479082188485[131] = 0.0;
   out_96002479082188485[132] = 0.0;
   out_96002479082188485[133] = 1.0;
   out_96002479082188485[134] = 0.0;
   out_96002479082188485[135] = 0.0;
   out_96002479082188485[136] = 0.0;
   out_96002479082188485[137] = 0.0;
   out_96002479082188485[138] = 0.0;
   out_96002479082188485[139] = 0.0;
   out_96002479082188485[140] = 0.0;
   out_96002479082188485[141] = 0.0;
   out_96002479082188485[142] = 0.0;
   out_96002479082188485[143] = 0.0;
   out_96002479082188485[144] = 0.0;
   out_96002479082188485[145] = 0.0;
   out_96002479082188485[146] = 0.0;
   out_96002479082188485[147] = 0.0;
   out_96002479082188485[148] = 0.0;
   out_96002479082188485[149] = 0.0;
   out_96002479082188485[150] = 0.0;
   out_96002479082188485[151] = 0.0;
   out_96002479082188485[152] = 1.0;
   out_96002479082188485[153] = 0.0;
   out_96002479082188485[154] = 0.0;
   out_96002479082188485[155] = 0.0;
   out_96002479082188485[156] = 0.0;
   out_96002479082188485[157] = 0.0;
   out_96002479082188485[158] = 0.0;
   out_96002479082188485[159] = 0.0;
   out_96002479082188485[160] = 0.0;
   out_96002479082188485[161] = 0.0;
   out_96002479082188485[162] = 0.0;
   out_96002479082188485[163] = 0.0;
   out_96002479082188485[164] = 0.0;
   out_96002479082188485[165] = 0.0;
   out_96002479082188485[166] = 0.0;
   out_96002479082188485[167] = 0.0;
   out_96002479082188485[168] = 0.0;
   out_96002479082188485[169] = 0.0;
   out_96002479082188485[170] = 0.0;
   out_96002479082188485[171] = 1.0;
   out_96002479082188485[172] = 0.0;
   out_96002479082188485[173] = 0.0;
   out_96002479082188485[174] = 0.0;
   out_96002479082188485[175] = 0.0;
   out_96002479082188485[176] = 0.0;
   out_96002479082188485[177] = 0.0;
   out_96002479082188485[178] = 0.0;
   out_96002479082188485[179] = 0.0;
   out_96002479082188485[180] = 0.0;
   out_96002479082188485[181] = 0.0;
   out_96002479082188485[182] = 0.0;
   out_96002479082188485[183] = 0.0;
   out_96002479082188485[184] = 0.0;
   out_96002479082188485[185] = 0.0;
   out_96002479082188485[186] = 0.0;
   out_96002479082188485[187] = 0.0;
   out_96002479082188485[188] = 0.0;
   out_96002479082188485[189] = 0.0;
   out_96002479082188485[190] = 1.0;
   out_96002479082188485[191] = 0.0;
   out_96002479082188485[192] = 0.0;
   out_96002479082188485[193] = 0.0;
   out_96002479082188485[194] = 0.0;
   out_96002479082188485[195] = 0.0;
   out_96002479082188485[196] = 0.0;
   out_96002479082188485[197] = 0.0;
   out_96002479082188485[198] = 0.0;
   out_96002479082188485[199] = 0.0;
   out_96002479082188485[200] = 0.0;
   out_96002479082188485[201] = 0.0;
   out_96002479082188485[202] = 0.0;
   out_96002479082188485[203] = 0.0;
   out_96002479082188485[204] = 0.0;
   out_96002479082188485[205] = 0.0;
   out_96002479082188485[206] = 0.0;
   out_96002479082188485[207] = 0.0;
   out_96002479082188485[208] = 0.0;
   out_96002479082188485[209] = 1.0;
   out_96002479082188485[210] = 0.0;
   out_96002479082188485[211] = 0.0;
   out_96002479082188485[212] = 0.0;
   out_96002479082188485[213] = 0.0;
   out_96002479082188485[214] = 0.0;
   out_96002479082188485[215] = 0.0;
   out_96002479082188485[216] = 0.0;
   out_96002479082188485[217] = 0.0;
   out_96002479082188485[218] = 0.0;
   out_96002479082188485[219] = 0.0;
   out_96002479082188485[220] = 0.0;
   out_96002479082188485[221] = 0.0;
   out_96002479082188485[222] = 0.0;
   out_96002479082188485[223] = 0.0;
   out_96002479082188485[224] = 0.0;
   out_96002479082188485[225] = 0.0;
   out_96002479082188485[226] = 0.0;
   out_96002479082188485[227] = 0.0;
   out_96002479082188485[228] = 1.0;
   out_96002479082188485[229] = 0.0;
   out_96002479082188485[230] = 0.0;
   out_96002479082188485[231] = 0.0;
   out_96002479082188485[232] = 0.0;
   out_96002479082188485[233] = 0.0;
   out_96002479082188485[234] = 0.0;
   out_96002479082188485[235] = 0.0;
   out_96002479082188485[236] = 0.0;
   out_96002479082188485[237] = 0.0;
   out_96002479082188485[238] = 0.0;
   out_96002479082188485[239] = 0.0;
   out_96002479082188485[240] = 0.0;
   out_96002479082188485[241] = 0.0;
   out_96002479082188485[242] = 0.0;
   out_96002479082188485[243] = 0.0;
   out_96002479082188485[244] = 0.0;
   out_96002479082188485[245] = 0.0;
   out_96002479082188485[246] = 0.0;
   out_96002479082188485[247] = 1.0;
   out_96002479082188485[248] = 0.0;
   out_96002479082188485[249] = 0.0;
   out_96002479082188485[250] = 0.0;
   out_96002479082188485[251] = 0.0;
   out_96002479082188485[252] = 0.0;
   out_96002479082188485[253] = 0.0;
   out_96002479082188485[254] = 0.0;
   out_96002479082188485[255] = 0.0;
   out_96002479082188485[256] = 0.0;
   out_96002479082188485[257] = 0.0;
   out_96002479082188485[258] = 0.0;
   out_96002479082188485[259] = 0.0;
   out_96002479082188485[260] = 0.0;
   out_96002479082188485[261] = 0.0;
   out_96002479082188485[262] = 0.0;
   out_96002479082188485[263] = 0.0;
   out_96002479082188485[264] = 0.0;
   out_96002479082188485[265] = 0.0;
   out_96002479082188485[266] = 1.0;
   out_96002479082188485[267] = 0.0;
   out_96002479082188485[268] = 0.0;
   out_96002479082188485[269] = 0.0;
   out_96002479082188485[270] = 0.0;
   out_96002479082188485[271] = 0.0;
   out_96002479082188485[272] = 0.0;
   out_96002479082188485[273] = 0.0;
   out_96002479082188485[274] = 0.0;
   out_96002479082188485[275] = 0.0;
   out_96002479082188485[276] = 0.0;
   out_96002479082188485[277] = 0.0;
   out_96002479082188485[278] = 0.0;
   out_96002479082188485[279] = 0.0;
   out_96002479082188485[280] = 0.0;
   out_96002479082188485[281] = 0.0;
   out_96002479082188485[282] = 0.0;
   out_96002479082188485[283] = 0.0;
   out_96002479082188485[284] = 0.0;
   out_96002479082188485[285] = 1.0;
   out_96002479082188485[286] = 0.0;
   out_96002479082188485[287] = 0.0;
   out_96002479082188485[288] = 0.0;
   out_96002479082188485[289] = 0.0;
   out_96002479082188485[290] = 0.0;
   out_96002479082188485[291] = 0.0;
   out_96002479082188485[292] = 0.0;
   out_96002479082188485[293] = 0.0;
   out_96002479082188485[294] = 0.0;
   out_96002479082188485[295] = 0.0;
   out_96002479082188485[296] = 0.0;
   out_96002479082188485[297] = 0.0;
   out_96002479082188485[298] = 0.0;
   out_96002479082188485[299] = 0.0;
   out_96002479082188485[300] = 0.0;
   out_96002479082188485[301] = 0.0;
   out_96002479082188485[302] = 0.0;
   out_96002479082188485[303] = 0.0;
   out_96002479082188485[304] = 1.0;
   out_96002479082188485[305] = 0.0;
   out_96002479082188485[306] = 0.0;
   out_96002479082188485[307] = 0.0;
   out_96002479082188485[308] = 0.0;
   out_96002479082188485[309] = 0.0;
   out_96002479082188485[310] = 0.0;
   out_96002479082188485[311] = 0.0;
   out_96002479082188485[312] = 0.0;
   out_96002479082188485[313] = 0.0;
   out_96002479082188485[314] = 0.0;
   out_96002479082188485[315] = 0.0;
   out_96002479082188485[316] = 0.0;
   out_96002479082188485[317] = 0.0;
   out_96002479082188485[318] = 0.0;
   out_96002479082188485[319] = 0.0;
   out_96002479082188485[320] = 0.0;
   out_96002479082188485[321] = 0.0;
   out_96002479082188485[322] = 0.0;
   out_96002479082188485[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8888553933023554192) {
   out_8888553933023554192[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8888553933023554192[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8888553933023554192[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8888553933023554192[3] = dt*state[12] + state[3];
   out_8888553933023554192[4] = dt*state[13] + state[4];
   out_8888553933023554192[5] = dt*state[14] + state[5];
   out_8888553933023554192[6] = state[6];
   out_8888553933023554192[7] = state[7];
   out_8888553933023554192[8] = state[8];
   out_8888553933023554192[9] = state[9];
   out_8888553933023554192[10] = state[10];
   out_8888553933023554192[11] = state[11];
   out_8888553933023554192[12] = state[12];
   out_8888553933023554192[13] = state[13];
   out_8888553933023554192[14] = state[14];
   out_8888553933023554192[15] = state[15];
   out_8888553933023554192[16] = state[16];
   out_8888553933023554192[17] = state[17];
}
void F_fun(double *state, double dt, double *out_3793856272932959588) {
   out_3793856272932959588[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3793856272932959588[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3793856272932959588[2] = 0;
   out_3793856272932959588[3] = 0;
   out_3793856272932959588[4] = 0;
   out_3793856272932959588[5] = 0;
   out_3793856272932959588[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3793856272932959588[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3793856272932959588[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3793856272932959588[9] = 0;
   out_3793856272932959588[10] = 0;
   out_3793856272932959588[11] = 0;
   out_3793856272932959588[12] = 0;
   out_3793856272932959588[13] = 0;
   out_3793856272932959588[14] = 0;
   out_3793856272932959588[15] = 0;
   out_3793856272932959588[16] = 0;
   out_3793856272932959588[17] = 0;
   out_3793856272932959588[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3793856272932959588[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3793856272932959588[20] = 0;
   out_3793856272932959588[21] = 0;
   out_3793856272932959588[22] = 0;
   out_3793856272932959588[23] = 0;
   out_3793856272932959588[24] = 0;
   out_3793856272932959588[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3793856272932959588[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3793856272932959588[27] = 0;
   out_3793856272932959588[28] = 0;
   out_3793856272932959588[29] = 0;
   out_3793856272932959588[30] = 0;
   out_3793856272932959588[31] = 0;
   out_3793856272932959588[32] = 0;
   out_3793856272932959588[33] = 0;
   out_3793856272932959588[34] = 0;
   out_3793856272932959588[35] = 0;
   out_3793856272932959588[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3793856272932959588[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3793856272932959588[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3793856272932959588[39] = 0;
   out_3793856272932959588[40] = 0;
   out_3793856272932959588[41] = 0;
   out_3793856272932959588[42] = 0;
   out_3793856272932959588[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3793856272932959588[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3793856272932959588[45] = 0;
   out_3793856272932959588[46] = 0;
   out_3793856272932959588[47] = 0;
   out_3793856272932959588[48] = 0;
   out_3793856272932959588[49] = 0;
   out_3793856272932959588[50] = 0;
   out_3793856272932959588[51] = 0;
   out_3793856272932959588[52] = 0;
   out_3793856272932959588[53] = 0;
   out_3793856272932959588[54] = 0;
   out_3793856272932959588[55] = 0;
   out_3793856272932959588[56] = 0;
   out_3793856272932959588[57] = 1;
   out_3793856272932959588[58] = 0;
   out_3793856272932959588[59] = 0;
   out_3793856272932959588[60] = 0;
   out_3793856272932959588[61] = 0;
   out_3793856272932959588[62] = 0;
   out_3793856272932959588[63] = 0;
   out_3793856272932959588[64] = 0;
   out_3793856272932959588[65] = 0;
   out_3793856272932959588[66] = dt;
   out_3793856272932959588[67] = 0;
   out_3793856272932959588[68] = 0;
   out_3793856272932959588[69] = 0;
   out_3793856272932959588[70] = 0;
   out_3793856272932959588[71] = 0;
   out_3793856272932959588[72] = 0;
   out_3793856272932959588[73] = 0;
   out_3793856272932959588[74] = 0;
   out_3793856272932959588[75] = 0;
   out_3793856272932959588[76] = 1;
   out_3793856272932959588[77] = 0;
   out_3793856272932959588[78] = 0;
   out_3793856272932959588[79] = 0;
   out_3793856272932959588[80] = 0;
   out_3793856272932959588[81] = 0;
   out_3793856272932959588[82] = 0;
   out_3793856272932959588[83] = 0;
   out_3793856272932959588[84] = 0;
   out_3793856272932959588[85] = dt;
   out_3793856272932959588[86] = 0;
   out_3793856272932959588[87] = 0;
   out_3793856272932959588[88] = 0;
   out_3793856272932959588[89] = 0;
   out_3793856272932959588[90] = 0;
   out_3793856272932959588[91] = 0;
   out_3793856272932959588[92] = 0;
   out_3793856272932959588[93] = 0;
   out_3793856272932959588[94] = 0;
   out_3793856272932959588[95] = 1;
   out_3793856272932959588[96] = 0;
   out_3793856272932959588[97] = 0;
   out_3793856272932959588[98] = 0;
   out_3793856272932959588[99] = 0;
   out_3793856272932959588[100] = 0;
   out_3793856272932959588[101] = 0;
   out_3793856272932959588[102] = 0;
   out_3793856272932959588[103] = 0;
   out_3793856272932959588[104] = dt;
   out_3793856272932959588[105] = 0;
   out_3793856272932959588[106] = 0;
   out_3793856272932959588[107] = 0;
   out_3793856272932959588[108] = 0;
   out_3793856272932959588[109] = 0;
   out_3793856272932959588[110] = 0;
   out_3793856272932959588[111] = 0;
   out_3793856272932959588[112] = 0;
   out_3793856272932959588[113] = 0;
   out_3793856272932959588[114] = 1;
   out_3793856272932959588[115] = 0;
   out_3793856272932959588[116] = 0;
   out_3793856272932959588[117] = 0;
   out_3793856272932959588[118] = 0;
   out_3793856272932959588[119] = 0;
   out_3793856272932959588[120] = 0;
   out_3793856272932959588[121] = 0;
   out_3793856272932959588[122] = 0;
   out_3793856272932959588[123] = 0;
   out_3793856272932959588[124] = 0;
   out_3793856272932959588[125] = 0;
   out_3793856272932959588[126] = 0;
   out_3793856272932959588[127] = 0;
   out_3793856272932959588[128] = 0;
   out_3793856272932959588[129] = 0;
   out_3793856272932959588[130] = 0;
   out_3793856272932959588[131] = 0;
   out_3793856272932959588[132] = 0;
   out_3793856272932959588[133] = 1;
   out_3793856272932959588[134] = 0;
   out_3793856272932959588[135] = 0;
   out_3793856272932959588[136] = 0;
   out_3793856272932959588[137] = 0;
   out_3793856272932959588[138] = 0;
   out_3793856272932959588[139] = 0;
   out_3793856272932959588[140] = 0;
   out_3793856272932959588[141] = 0;
   out_3793856272932959588[142] = 0;
   out_3793856272932959588[143] = 0;
   out_3793856272932959588[144] = 0;
   out_3793856272932959588[145] = 0;
   out_3793856272932959588[146] = 0;
   out_3793856272932959588[147] = 0;
   out_3793856272932959588[148] = 0;
   out_3793856272932959588[149] = 0;
   out_3793856272932959588[150] = 0;
   out_3793856272932959588[151] = 0;
   out_3793856272932959588[152] = 1;
   out_3793856272932959588[153] = 0;
   out_3793856272932959588[154] = 0;
   out_3793856272932959588[155] = 0;
   out_3793856272932959588[156] = 0;
   out_3793856272932959588[157] = 0;
   out_3793856272932959588[158] = 0;
   out_3793856272932959588[159] = 0;
   out_3793856272932959588[160] = 0;
   out_3793856272932959588[161] = 0;
   out_3793856272932959588[162] = 0;
   out_3793856272932959588[163] = 0;
   out_3793856272932959588[164] = 0;
   out_3793856272932959588[165] = 0;
   out_3793856272932959588[166] = 0;
   out_3793856272932959588[167] = 0;
   out_3793856272932959588[168] = 0;
   out_3793856272932959588[169] = 0;
   out_3793856272932959588[170] = 0;
   out_3793856272932959588[171] = 1;
   out_3793856272932959588[172] = 0;
   out_3793856272932959588[173] = 0;
   out_3793856272932959588[174] = 0;
   out_3793856272932959588[175] = 0;
   out_3793856272932959588[176] = 0;
   out_3793856272932959588[177] = 0;
   out_3793856272932959588[178] = 0;
   out_3793856272932959588[179] = 0;
   out_3793856272932959588[180] = 0;
   out_3793856272932959588[181] = 0;
   out_3793856272932959588[182] = 0;
   out_3793856272932959588[183] = 0;
   out_3793856272932959588[184] = 0;
   out_3793856272932959588[185] = 0;
   out_3793856272932959588[186] = 0;
   out_3793856272932959588[187] = 0;
   out_3793856272932959588[188] = 0;
   out_3793856272932959588[189] = 0;
   out_3793856272932959588[190] = 1;
   out_3793856272932959588[191] = 0;
   out_3793856272932959588[192] = 0;
   out_3793856272932959588[193] = 0;
   out_3793856272932959588[194] = 0;
   out_3793856272932959588[195] = 0;
   out_3793856272932959588[196] = 0;
   out_3793856272932959588[197] = 0;
   out_3793856272932959588[198] = 0;
   out_3793856272932959588[199] = 0;
   out_3793856272932959588[200] = 0;
   out_3793856272932959588[201] = 0;
   out_3793856272932959588[202] = 0;
   out_3793856272932959588[203] = 0;
   out_3793856272932959588[204] = 0;
   out_3793856272932959588[205] = 0;
   out_3793856272932959588[206] = 0;
   out_3793856272932959588[207] = 0;
   out_3793856272932959588[208] = 0;
   out_3793856272932959588[209] = 1;
   out_3793856272932959588[210] = 0;
   out_3793856272932959588[211] = 0;
   out_3793856272932959588[212] = 0;
   out_3793856272932959588[213] = 0;
   out_3793856272932959588[214] = 0;
   out_3793856272932959588[215] = 0;
   out_3793856272932959588[216] = 0;
   out_3793856272932959588[217] = 0;
   out_3793856272932959588[218] = 0;
   out_3793856272932959588[219] = 0;
   out_3793856272932959588[220] = 0;
   out_3793856272932959588[221] = 0;
   out_3793856272932959588[222] = 0;
   out_3793856272932959588[223] = 0;
   out_3793856272932959588[224] = 0;
   out_3793856272932959588[225] = 0;
   out_3793856272932959588[226] = 0;
   out_3793856272932959588[227] = 0;
   out_3793856272932959588[228] = 1;
   out_3793856272932959588[229] = 0;
   out_3793856272932959588[230] = 0;
   out_3793856272932959588[231] = 0;
   out_3793856272932959588[232] = 0;
   out_3793856272932959588[233] = 0;
   out_3793856272932959588[234] = 0;
   out_3793856272932959588[235] = 0;
   out_3793856272932959588[236] = 0;
   out_3793856272932959588[237] = 0;
   out_3793856272932959588[238] = 0;
   out_3793856272932959588[239] = 0;
   out_3793856272932959588[240] = 0;
   out_3793856272932959588[241] = 0;
   out_3793856272932959588[242] = 0;
   out_3793856272932959588[243] = 0;
   out_3793856272932959588[244] = 0;
   out_3793856272932959588[245] = 0;
   out_3793856272932959588[246] = 0;
   out_3793856272932959588[247] = 1;
   out_3793856272932959588[248] = 0;
   out_3793856272932959588[249] = 0;
   out_3793856272932959588[250] = 0;
   out_3793856272932959588[251] = 0;
   out_3793856272932959588[252] = 0;
   out_3793856272932959588[253] = 0;
   out_3793856272932959588[254] = 0;
   out_3793856272932959588[255] = 0;
   out_3793856272932959588[256] = 0;
   out_3793856272932959588[257] = 0;
   out_3793856272932959588[258] = 0;
   out_3793856272932959588[259] = 0;
   out_3793856272932959588[260] = 0;
   out_3793856272932959588[261] = 0;
   out_3793856272932959588[262] = 0;
   out_3793856272932959588[263] = 0;
   out_3793856272932959588[264] = 0;
   out_3793856272932959588[265] = 0;
   out_3793856272932959588[266] = 1;
   out_3793856272932959588[267] = 0;
   out_3793856272932959588[268] = 0;
   out_3793856272932959588[269] = 0;
   out_3793856272932959588[270] = 0;
   out_3793856272932959588[271] = 0;
   out_3793856272932959588[272] = 0;
   out_3793856272932959588[273] = 0;
   out_3793856272932959588[274] = 0;
   out_3793856272932959588[275] = 0;
   out_3793856272932959588[276] = 0;
   out_3793856272932959588[277] = 0;
   out_3793856272932959588[278] = 0;
   out_3793856272932959588[279] = 0;
   out_3793856272932959588[280] = 0;
   out_3793856272932959588[281] = 0;
   out_3793856272932959588[282] = 0;
   out_3793856272932959588[283] = 0;
   out_3793856272932959588[284] = 0;
   out_3793856272932959588[285] = 1;
   out_3793856272932959588[286] = 0;
   out_3793856272932959588[287] = 0;
   out_3793856272932959588[288] = 0;
   out_3793856272932959588[289] = 0;
   out_3793856272932959588[290] = 0;
   out_3793856272932959588[291] = 0;
   out_3793856272932959588[292] = 0;
   out_3793856272932959588[293] = 0;
   out_3793856272932959588[294] = 0;
   out_3793856272932959588[295] = 0;
   out_3793856272932959588[296] = 0;
   out_3793856272932959588[297] = 0;
   out_3793856272932959588[298] = 0;
   out_3793856272932959588[299] = 0;
   out_3793856272932959588[300] = 0;
   out_3793856272932959588[301] = 0;
   out_3793856272932959588[302] = 0;
   out_3793856272932959588[303] = 0;
   out_3793856272932959588[304] = 1;
   out_3793856272932959588[305] = 0;
   out_3793856272932959588[306] = 0;
   out_3793856272932959588[307] = 0;
   out_3793856272932959588[308] = 0;
   out_3793856272932959588[309] = 0;
   out_3793856272932959588[310] = 0;
   out_3793856272932959588[311] = 0;
   out_3793856272932959588[312] = 0;
   out_3793856272932959588[313] = 0;
   out_3793856272932959588[314] = 0;
   out_3793856272932959588[315] = 0;
   out_3793856272932959588[316] = 0;
   out_3793856272932959588[317] = 0;
   out_3793856272932959588[318] = 0;
   out_3793856272932959588[319] = 0;
   out_3793856272932959588[320] = 0;
   out_3793856272932959588[321] = 0;
   out_3793856272932959588[322] = 0;
   out_3793856272932959588[323] = 1;
}
void h_4(double *state, double *unused, double *out_10924150640940683) {
   out_10924150640940683[0] = state[6] + state[9];
   out_10924150640940683[1] = state[7] + state[10];
   out_10924150640940683[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_5752079327669770236) {
   out_5752079327669770236[0] = 0;
   out_5752079327669770236[1] = 0;
   out_5752079327669770236[2] = 0;
   out_5752079327669770236[3] = 0;
   out_5752079327669770236[4] = 0;
   out_5752079327669770236[5] = 0;
   out_5752079327669770236[6] = 1;
   out_5752079327669770236[7] = 0;
   out_5752079327669770236[8] = 0;
   out_5752079327669770236[9] = 1;
   out_5752079327669770236[10] = 0;
   out_5752079327669770236[11] = 0;
   out_5752079327669770236[12] = 0;
   out_5752079327669770236[13] = 0;
   out_5752079327669770236[14] = 0;
   out_5752079327669770236[15] = 0;
   out_5752079327669770236[16] = 0;
   out_5752079327669770236[17] = 0;
   out_5752079327669770236[18] = 0;
   out_5752079327669770236[19] = 0;
   out_5752079327669770236[20] = 0;
   out_5752079327669770236[21] = 0;
   out_5752079327669770236[22] = 0;
   out_5752079327669770236[23] = 0;
   out_5752079327669770236[24] = 0;
   out_5752079327669770236[25] = 1;
   out_5752079327669770236[26] = 0;
   out_5752079327669770236[27] = 0;
   out_5752079327669770236[28] = 1;
   out_5752079327669770236[29] = 0;
   out_5752079327669770236[30] = 0;
   out_5752079327669770236[31] = 0;
   out_5752079327669770236[32] = 0;
   out_5752079327669770236[33] = 0;
   out_5752079327669770236[34] = 0;
   out_5752079327669770236[35] = 0;
   out_5752079327669770236[36] = 0;
   out_5752079327669770236[37] = 0;
   out_5752079327669770236[38] = 0;
   out_5752079327669770236[39] = 0;
   out_5752079327669770236[40] = 0;
   out_5752079327669770236[41] = 0;
   out_5752079327669770236[42] = 0;
   out_5752079327669770236[43] = 0;
   out_5752079327669770236[44] = 1;
   out_5752079327669770236[45] = 0;
   out_5752079327669770236[46] = 0;
   out_5752079327669770236[47] = 1;
   out_5752079327669770236[48] = 0;
   out_5752079327669770236[49] = 0;
   out_5752079327669770236[50] = 0;
   out_5752079327669770236[51] = 0;
   out_5752079327669770236[52] = 0;
   out_5752079327669770236[53] = 0;
}
void h_10(double *state, double *unused, double *out_3400315615895606338) {
   out_3400315615895606338[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_3400315615895606338[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_3400315615895606338[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_6603039364318987837) {
   out_6603039364318987837[0] = 0;
   out_6603039364318987837[1] = 9.8100000000000005*cos(state[1]);
   out_6603039364318987837[2] = 0;
   out_6603039364318987837[3] = 0;
   out_6603039364318987837[4] = -state[8];
   out_6603039364318987837[5] = state[7];
   out_6603039364318987837[6] = 0;
   out_6603039364318987837[7] = state[5];
   out_6603039364318987837[8] = -state[4];
   out_6603039364318987837[9] = 0;
   out_6603039364318987837[10] = 0;
   out_6603039364318987837[11] = 0;
   out_6603039364318987837[12] = 1;
   out_6603039364318987837[13] = 0;
   out_6603039364318987837[14] = 0;
   out_6603039364318987837[15] = 1;
   out_6603039364318987837[16] = 0;
   out_6603039364318987837[17] = 0;
   out_6603039364318987837[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_6603039364318987837[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_6603039364318987837[20] = 0;
   out_6603039364318987837[21] = state[8];
   out_6603039364318987837[22] = 0;
   out_6603039364318987837[23] = -state[6];
   out_6603039364318987837[24] = -state[5];
   out_6603039364318987837[25] = 0;
   out_6603039364318987837[26] = state[3];
   out_6603039364318987837[27] = 0;
   out_6603039364318987837[28] = 0;
   out_6603039364318987837[29] = 0;
   out_6603039364318987837[30] = 0;
   out_6603039364318987837[31] = 1;
   out_6603039364318987837[32] = 0;
   out_6603039364318987837[33] = 0;
   out_6603039364318987837[34] = 1;
   out_6603039364318987837[35] = 0;
   out_6603039364318987837[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_6603039364318987837[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_6603039364318987837[38] = 0;
   out_6603039364318987837[39] = -state[7];
   out_6603039364318987837[40] = state[6];
   out_6603039364318987837[41] = 0;
   out_6603039364318987837[42] = state[4];
   out_6603039364318987837[43] = -state[3];
   out_6603039364318987837[44] = 0;
   out_6603039364318987837[45] = 0;
   out_6603039364318987837[46] = 0;
   out_6603039364318987837[47] = 0;
   out_6603039364318987837[48] = 0;
   out_6603039364318987837[49] = 0;
   out_6603039364318987837[50] = 1;
   out_6603039364318987837[51] = 0;
   out_6603039364318987837[52] = 0;
   out_6603039364318987837[53] = 1;
}
void h_13(double *state, double *unused, double *out_5162106749790850325) {
   out_5162106749790850325[0] = state[3];
   out_5162106749790850325[1] = state[4];
   out_5162106749790850325[2] = state[5];
}
void H_13(double *state, double *unused, double *out_2539805502337437435) {
   out_2539805502337437435[0] = 0;
   out_2539805502337437435[1] = 0;
   out_2539805502337437435[2] = 0;
   out_2539805502337437435[3] = 1;
   out_2539805502337437435[4] = 0;
   out_2539805502337437435[5] = 0;
   out_2539805502337437435[6] = 0;
   out_2539805502337437435[7] = 0;
   out_2539805502337437435[8] = 0;
   out_2539805502337437435[9] = 0;
   out_2539805502337437435[10] = 0;
   out_2539805502337437435[11] = 0;
   out_2539805502337437435[12] = 0;
   out_2539805502337437435[13] = 0;
   out_2539805502337437435[14] = 0;
   out_2539805502337437435[15] = 0;
   out_2539805502337437435[16] = 0;
   out_2539805502337437435[17] = 0;
   out_2539805502337437435[18] = 0;
   out_2539805502337437435[19] = 0;
   out_2539805502337437435[20] = 0;
   out_2539805502337437435[21] = 0;
   out_2539805502337437435[22] = 1;
   out_2539805502337437435[23] = 0;
   out_2539805502337437435[24] = 0;
   out_2539805502337437435[25] = 0;
   out_2539805502337437435[26] = 0;
   out_2539805502337437435[27] = 0;
   out_2539805502337437435[28] = 0;
   out_2539805502337437435[29] = 0;
   out_2539805502337437435[30] = 0;
   out_2539805502337437435[31] = 0;
   out_2539805502337437435[32] = 0;
   out_2539805502337437435[33] = 0;
   out_2539805502337437435[34] = 0;
   out_2539805502337437435[35] = 0;
   out_2539805502337437435[36] = 0;
   out_2539805502337437435[37] = 0;
   out_2539805502337437435[38] = 0;
   out_2539805502337437435[39] = 0;
   out_2539805502337437435[40] = 0;
   out_2539805502337437435[41] = 1;
   out_2539805502337437435[42] = 0;
   out_2539805502337437435[43] = 0;
   out_2539805502337437435[44] = 0;
   out_2539805502337437435[45] = 0;
   out_2539805502337437435[46] = 0;
   out_2539805502337437435[47] = 0;
   out_2539805502337437435[48] = 0;
   out_2539805502337437435[49] = 0;
   out_2539805502337437435[50] = 0;
   out_2539805502337437435[51] = 0;
   out_2539805502337437435[52] = 0;
   out_2539805502337437435[53] = 0;
}
void h_14(double *state, double *unused, double *out_8034891048701220434) {
   out_8034891048701220434[0] = state[6];
   out_8034891048701220434[1] = state[7];
   out_8034891048701220434[2] = state[8];
}
void H_14(double *state, double *unused, double *out_1788838471330285707) {
   out_1788838471330285707[0] = 0;
   out_1788838471330285707[1] = 0;
   out_1788838471330285707[2] = 0;
   out_1788838471330285707[3] = 0;
   out_1788838471330285707[4] = 0;
   out_1788838471330285707[5] = 0;
   out_1788838471330285707[6] = 1;
   out_1788838471330285707[7] = 0;
   out_1788838471330285707[8] = 0;
   out_1788838471330285707[9] = 0;
   out_1788838471330285707[10] = 0;
   out_1788838471330285707[11] = 0;
   out_1788838471330285707[12] = 0;
   out_1788838471330285707[13] = 0;
   out_1788838471330285707[14] = 0;
   out_1788838471330285707[15] = 0;
   out_1788838471330285707[16] = 0;
   out_1788838471330285707[17] = 0;
   out_1788838471330285707[18] = 0;
   out_1788838471330285707[19] = 0;
   out_1788838471330285707[20] = 0;
   out_1788838471330285707[21] = 0;
   out_1788838471330285707[22] = 0;
   out_1788838471330285707[23] = 0;
   out_1788838471330285707[24] = 0;
   out_1788838471330285707[25] = 1;
   out_1788838471330285707[26] = 0;
   out_1788838471330285707[27] = 0;
   out_1788838471330285707[28] = 0;
   out_1788838471330285707[29] = 0;
   out_1788838471330285707[30] = 0;
   out_1788838471330285707[31] = 0;
   out_1788838471330285707[32] = 0;
   out_1788838471330285707[33] = 0;
   out_1788838471330285707[34] = 0;
   out_1788838471330285707[35] = 0;
   out_1788838471330285707[36] = 0;
   out_1788838471330285707[37] = 0;
   out_1788838471330285707[38] = 0;
   out_1788838471330285707[39] = 0;
   out_1788838471330285707[40] = 0;
   out_1788838471330285707[41] = 0;
   out_1788838471330285707[42] = 0;
   out_1788838471330285707[43] = 0;
   out_1788838471330285707[44] = 1;
   out_1788838471330285707[45] = 0;
   out_1788838471330285707[46] = 0;
   out_1788838471330285707[47] = 0;
   out_1788838471330285707[48] = 0;
   out_1788838471330285707[49] = 0;
   out_1788838471330285707[50] = 0;
   out_1788838471330285707[51] = 0;
   out_1788838471330285707[52] = 0;
   out_1788838471330285707[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_3094993718265680010) {
  err_fun(nom_x, delta_x, out_3094993718265680010);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_446507105452282601) {
  inv_err_fun(nom_x, true_x, out_446507105452282601);
}
void pose_H_mod_fun(double *state, double *out_96002479082188485) {
  H_mod_fun(state, out_96002479082188485);
}
void pose_f_fun(double *state, double dt, double *out_8888553933023554192) {
  f_fun(state,  dt, out_8888553933023554192);
}
void pose_F_fun(double *state, double dt, double *out_3793856272932959588) {
  F_fun(state,  dt, out_3793856272932959588);
}
void pose_h_4(double *state, double *unused, double *out_10924150640940683) {
  h_4(state, unused, out_10924150640940683);
}
void pose_H_4(double *state, double *unused, double *out_5752079327669770236) {
  H_4(state, unused, out_5752079327669770236);
}
void pose_h_10(double *state, double *unused, double *out_3400315615895606338) {
  h_10(state, unused, out_3400315615895606338);
}
void pose_H_10(double *state, double *unused, double *out_6603039364318987837) {
  H_10(state, unused, out_6603039364318987837);
}
void pose_h_13(double *state, double *unused, double *out_5162106749790850325) {
  h_13(state, unused, out_5162106749790850325);
}
void pose_H_13(double *state, double *unused, double *out_2539805502337437435) {
  H_13(state, unused, out_2539805502337437435);
}
void pose_h_14(double *state, double *unused, double *out_8034891048701220434) {
  h_14(state, unused, out_8034891048701220434);
}
void pose_H_14(double *state, double *unused, double *out_1788838471330285707) {
  H_14(state, unused, out_1788838471330285707);
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
