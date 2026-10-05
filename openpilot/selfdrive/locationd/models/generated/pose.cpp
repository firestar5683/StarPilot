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
void err_fun(double *nom_x, double *delta_x, double *out_8386835163844872263) {
   out_8386835163844872263[0] = delta_x[0] + nom_x[0];
   out_8386835163844872263[1] = delta_x[1] + nom_x[1];
   out_8386835163844872263[2] = delta_x[2] + nom_x[2];
   out_8386835163844872263[3] = delta_x[3] + nom_x[3];
   out_8386835163844872263[4] = delta_x[4] + nom_x[4];
   out_8386835163844872263[5] = delta_x[5] + nom_x[5];
   out_8386835163844872263[6] = delta_x[6] + nom_x[6];
   out_8386835163844872263[7] = delta_x[7] + nom_x[7];
   out_8386835163844872263[8] = delta_x[8] + nom_x[8];
   out_8386835163844872263[9] = delta_x[9] + nom_x[9];
   out_8386835163844872263[10] = delta_x[10] + nom_x[10];
   out_8386835163844872263[11] = delta_x[11] + nom_x[11];
   out_8386835163844872263[12] = delta_x[12] + nom_x[12];
   out_8386835163844872263[13] = delta_x[13] + nom_x[13];
   out_8386835163844872263[14] = delta_x[14] + nom_x[14];
   out_8386835163844872263[15] = delta_x[15] + nom_x[15];
   out_8386835163844872263[16] = delta_x[16] + nom_x[16];
   out_8386835163844872263[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_5826204590882848019) {
   out_5826204590882848019[0] = -nom_x[0] + true_x[0];
   out_5826204590882848019[1] = -nom_x[1] + true_x[1];
   out_5826204590882848019[2] = -nom_x[2] + true_x[2];
   out_5826204590882848019[3] = -nom_x[3] + true_x[3];
   out_5826204590882848019[4] = -nom_x[4] + true_x[4];
   out_5826204590882848019[5] = -nom_x[5] + true_x[5];
   out_5826204590882848019[6] = -nom_x[6] + true_x[6];
   out_5826204590882848019[7] = -nom_x[7] + true_x[7];
   out_5826204590882848019[8] = -nom_x[8] + true_x[8];
   out_5826204590882848019[9] = -nom_x[9] + true_x[9];
   out_5826204590882848019[10] = -nom_x[10] + true_x[10];
   out_5826204590882848019[11] = -nom_x[11] + true_x[11];
   out_5826204590882848019[12] = -nom_x[12] + true_x[12];
   out_5826204590882848019[13] = -nom_x[13] + true_x[13];
   out_5826204590882848019[14] = -nom_x[14] + true_x[14];
   out_5826204590882848019[15] = -nom_x[15] + true_x[15];
   out_5826204590882848019[16] = -nom_x[16] + true_x[16];
   out_5826204590882848019[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_7521593534267777079) {
   out_7521593534267777079[0] = 1.0;
   out_7521593534267777079[1] = 0.0;
   out_7521593534267777079[2] = 0.0;
   out_7521593534267777079[3] = 0.0;
   out_7521593534267777079[4] = 0.0;
   out_7521593534267777079[5] = 0.0;
   out_7521593534267777079[6] = 0.0;
   out_7521593534267777079[7] = 0.0;
   out_7521593534267777079[8] = 0.0;
   out_7521593534267777079[9] = 0.0;
   out_7521593534267777079[10] = 0.0;
   out_7521593534267777079[11] = 0.0;
   out_7521593534267777079[12] = 0.0;
   out_7521593534267777079[13] = 0.0;
   out_7521593534267777079[14] = 0.0;
   out_7521593534267777079[15] = 0.0;
   out_7521593534267777079[16] = 0.0;
   out_7521593534267777079[17] = 0.0;
   out_7521593534267777079[18] = 0.0;
   out_7521593534267777079[19] = 1.0;
   out_7521593534267777079[20] = 0.0;
   out_7521593534267777079[21] = 0.0;
   out_7521593534267777079[22] = 0.0;
   out_7521593534267777079[23] = 0.0;
   out_7521593534267777079[24] = 0.0;
   out_7521593534267777079[25] = 0.0;
   out_7521593534267777079[26] = 0.0;
   out_7521593534267777079[27] = 0.0;
   out_7521593534267777079[28] = 0.0;
   out_7521593534267777079[29] = 0.0;
   out_7521593534267777079[30] = 0.0;
   out_7521593534267777079[31] = 0.0;
   out_7521593534267777079[32] = 0.0;
   out_7521593534267777079[33] = 0.0;
   out_7521593534267777079[34] = 0.0;
   out_7521593534267777079[35] = 0.0;
   out_7521593534267777079[36] = 0.0;
   out_7521593534267777079[37] = 0.0;
   out_7521593534267777079[38] = 1.0;
   out_7521593534267777079[39] = 0.0;
   out_7521593534267777079[40] = 0.0;
   out_7521593534267777079[41] = 0.0;
   out_7521593534267777079[42] = 0.0;
   out_7521593534267777079[43] = 0.0;
   out_7521593534267777079[44] = 0.0;
   out_7521593534267777079[45] = 0.0;
   out_7521593534267777079[46] = 0.0;
   out_7521593534267777079[47] = 0.0;
   out_7521593534267777079[48] = 0.0;
   out_7521593534267777079[49] = 0.0;
   out_7521593534267777079[50] = 0.0;
   out_7521593534267777079[51] = 0.0;
   out_7521593534267777079[52] = 0.0;
   out_7521593534267777079[53] = 0.0;
   out_7521593534267777079[54] = 0.0;
   out_7521593534267777079[55] = 0.0;
   out_7521593534267777079[56] = 0.0;
   out_7521593534267777079[57] = 1.0;
   out_7521593534267777079[58] = 0.0;
   out_7521593534267777079[59] = 0.0;
   out_7521593534267777079[60] = 0.0;
   out_7521593534267777079[61] = 0.0;
   out_7521593534267777079[62] = 0.0;
   out_7521593534267777079[63] = 0.0;
   out_7521593534267777079[64] = 0.0;
   out_7521593534267777079[65] = 0.0;
   out_7521593534267777079[66] = 0.0;
   out_7521593534267777079[67] = 0.0;
   out_7521593534267777079[68] = 0.0;
   out_7521593534267777079[69] = 0.0;
   out_7521593534267777079[70] = 0.0;
   out_7521593534267777079[71] = 0.0;
   out_7521593534267777079[72] = 0.0;
   out_7521593534267777079[73] = 0.0;
   out_7521593534267777079[74] = 0.0;
   out_7521593534267777079[75] = 0.0;
   out_7521593534267777079[76] = 1.0;
   out_7521593534267777079[77] = 0.0;
   out_7521593534267777079[78] = 0.0;
   out_7521593534267777079[79] = 0.0;
   out_7521593534267777079[80] = 0.0;
   out_7521593534267777079[81] = 0.0;
   out_7521593534267777079[82] = 0.0;
   out_7521593534267777079[83] = 0.0;
   out_7521593534267777079[84] = 0.0;
   out_7521593534267777079[85] = 0.0;
   out_7521593534267777079[86] = 0.0;
   out_7521593534267777079[87] = 0.0;
   out_7521593534267777079[88] = 0.0;
   out_7521593534267777079[89] = 0.0;
   out_7521593534267777079[90] = 0.0;
   out_7521593534267777079[91] = 0.0;
   out_7521593534267777079[92] = 0.0;
   out_7521593534267777079[93] = 0.0;
   out_7521593534267777079[94] = 0.0;
   out_7521593534267777079[95] = 1.0;
   out_7521593534267777079[96] = 0.0;
   out_7521593534267777079[97] = 0.0;
   out_7521593534267777079[98] = 0.0;
   out_7521593534267777079[99] = 0.0;
   out_7521593534267777079[100] = 0.0;
   out_7521593534267777079[101] = 0.0;
   out_7521593534267777079[102] = 0.0;
   out_7521593534267777079[103] = 0.0;
   out_7521593534267777079[104] = 0.0;
   out_7521593534267777079[105] = 0.0;
   out_7521593534267777079[106] = 0.0;
   out_7521593534267777079[107] = 0.0;
   out_7521593534267777079[108] = 0.0;
   out_7521593534267777079[109] = 0.0;
   out_7521593534267777079[110] = 0.0;
   out_7521593534267777079[111] = 0.0;
   out_7521593534267777079[112] = 0.0;
   out_7521593534267777079[113] = 0.0;
   out_7521593534267777079[114] = 1.0;
   out_7521593534267777079[115] = 0.0;
   out_7521593534267777079[116] = 0.0;
   out_7521593534267777079[117] = 0.0;
   out_7521593534267777079[118] = 0.0;
   out_7521593534267777079[119] = 0.0;
   out_7521593534267777079[120] = 0.0;
   out_7521593534267777079[121] = 0.0;
   out_7521593534267777079[122] = 0.0;
   out_7521593534267777079[123] = 0.0;
   out_7521593534267777079[124] = 0.0;
   out_7521593534267777079[125] = 0.0;
   out_7521593534267777079[126] = 0.0;
   out_7521593534267777079[127] = 0.0;
   out_7521593534267777079[128] = 0.0;
   out_7521593534267777079[129] = 0.0;
   out_7521593534267777079[130] = 0.0;
   out_7521593534267777079[131] = 0.0;
   out_7521593534267777079[132] = 0.0;
   out_7521593534267777079[133] = 1.0;
   out_7521593534267777079[134] = 0.0;
   out_7521593534267777079[135] = 0.0;
   out_7521593534267777079[136] = 0.0;
   out_7521593534267777079[137] = 0.0;
   out_7521593534267777079[138] = 0.0;
   out_7521593534267777079[139] = 0.0;
   out_7521593534267777079[140] = 0.0;
   out_7521593534267777079[141] = 0.0;
   out_7521593534267777079[142] = 0.0;
   out_7521593534267777079[143] = 0.0;
   out_7521593534267777079[144] = 0.0;
   out_7521593534267777079[145] = 0.0;
   out_7521593534267777079[146] = 0.0;
   out_7521593534267777079[147] = 0.0;
   out_7521593534267777079[148] = 0.0;
   out_7521593534267777079[149] = 0.0;
   out_7521593534267777079[150] = 0.0;
   out_7521593534267777079[151] = 0.0;
   out_7521593534267777079[152] = 1.0;
   out_7521593534267777079[153] = 0.0;
   out_7521593534267777079[154] = 0.0;
   out_7521593534267777079[155] = 0.0;
   out_7521593534267777079[156] = 0.0;
   out_7521593534267777079[157] = 0.0;
   out_7521593534267777079[158] = 0.0;
   out_7521593534267777079[159] = 0.0;
   out_7521593534267777079[160] = 0.0;
   out_7521593534267777079[161] = 0.0;
   out_7521593534267777079[162] = 0.0;
   out_7521593534267777079[163] = 0.0;
   out_7521593534267777079[164] = 0.0;
   out_7521593534267777079[165] = 0.0;
   out_7521593534267777079[166] = 0.0;
   out_7521593534267777079[167] = 0.0;
   out_7521593534267777079[168] = 0.0;
   out_7521593534267777079[169] = 0.0;
   out_7521593534267777079[170] = 0.0;
   out_7521593534267777079[171] = 1.0;
   out_7521593534267777079[172] = 0.0;
   out_7521593534267777079[173] = 0.0;
   out_7521593534267777079[174] = 0.0;
   out_7521593534267777079[175] = 0.0;
   out_7521593534267777079[176] = 0.0;
   out_7521593534267777079[177] = 0.0;
   out_7521593534267777079[178] = 0.0;
   out_7521593534267777079[179] = 0.0;
   out_7521593534267777079[180] = 0.0;
   out_7521593534267777079[181] = 0.0;
   out_7521593534267777079[182] = 0.0;
   out_7521593534267777079[183] = 0.0;
   out_7521593534267777079[184] = 0.0;
   out_7521593534267777079[185] = 0.0;
   out_7521593534267777079[186] = 0.0;
   out_7521593534267777079[187] = 0.0;
   out_7521593534267777079[188] = 0.0;
   out_7521593534267777079[189] = 0.0;
   out_7521593534267777079[190] = 1.0;
   out_7521593534267777079[191] = 0.0;
   out_7521593534267777079[192] = 0.0;
   out_7521593534267777079[193] = 0.0;
   out_7521593534267777079[194] = 0.0;
   out_7521593534267777079[195] = 0.0;
   out_7521593534267777079[196] = 0.0;
   out_7521593534267777079[197] = 0.0;
   out_7521593534267777079[198] = 0.0;
   out_7521593534267777079[199] = 0.0;
   out_7521593534267777079[200] = 0.0;
   out_7521593534267777079[201] = 0.0;
   out_7521593534267777079[202] = 0.0;
   out_7521593534267777079[203] = 0.0;
   out_7521593534267777079[204] = 0.0;
   out_7521593534267777079[205] = 0.0;
   out_7521593534267777079[206] = 0.0;
   out_7521593534267777079[207] = 0.0;
   out_7521593534267777079[208] = 0.0;
   out_7521593534267777079[209] = 1.0;
   out_7521593534267777079[210] = 0.0;
   out_7521593534267777079[211] = 0.0;
   out_7521593534267777079[212] = 0.0;
   out_7521593534267777079[213] = 0.0;
   out_7521593534267777079[214] = 0.0;
   out_7521593534267777079[215] = 0.0;
   out_7521593534267777079[216] = 0.0;
   out_7521593534267777079[217] = 0.0;
   out_7521593534267777079[218] = 0.0;
   out_7521593534267777079[219] = 0.0;
   out_7521593534267777079[220] = 0.0;
   out_7521593534267777079[221] = 0.0;
   out_7521593534267777079[222] = 0.0;
   out_7521593534267777079[223] = 0.0;
   out_7521593534267777079[224] = 0.0;
   out_7521593534267777079[225] = 0.0;
   out_7521593534267777079[226] = 0.0;
   out_7521593534267777079[227] = 0.0;
   out_7521593534267777079[228] = 1.0;
   out_7521593534267777079[229] = 0.0;
   out_7521593534267777079[230] = 0.0;
   out_7521593534267777079[231] = 0.0;
   out_7521593534267777079[232] = 0.0;
   out_7521593534267777079[233] = 0.0;
   out_7521593534267777079[234] = 0.0;
   out_7521593534267777079[235] = 0.0;
   out_7521593534267777079[236] = 0.0;
   out_7521593534267777079[237] = 0.0;
   out_7521593534267777079[238] = 0.0;
   out_7521593534267777079[239] = 0.0;
   out_7521593534267777079[240] = 0.0;
   out_7521593534267777079[241] = 0.0;
   out_7521593534267777079[242] = 0.0;
   out_7521593534267777079[243] = 0.0;
   out_7521593534267777079[244] = 0.0;
   out_7521593534267777079[245] = 0.0;
   out_7521593534267777079[246] = 0.0;
   out_7521593534267777079[247] = 1.0;
   out_7521593534267777079[248] = 0.0;
   out_7521593534267777079[249] = 0.0;
   out_7521593534267777079[250] = 0.0;
   out_7521593534267777079[251] = 0.0;
   out_7521593534267777079[252] = 0.0;
   out_7521593534267777079[253] = 0.0;
   out_7521593534267777079[254] = 0.0;
   out_7521593534267777079[255] = 0.0;
   out_7521593534267777079[256] = 0.0;
   out_7521593534267777079[257] = 0.0;
   out_7521593534267777079[258] = 0.0;
   out_7521593534267777079[259] = 0.0;
   out_7521593534267777079[260] = 0.0;
   out_7521593534267777079[261] = 0.0;
   out_7521593534267777079[262] = 0.0;
   out_7521593534267777079[263] = 0.0;
   out_7521593534267777079[264] = 0.0;
   out_7521593534267777079[265] = 0.0;
   out_7521593534267777079[266] = 1.0;
   out_7521593534267777079[267] = 0.0;
   out_7521593534267777079[268] = 0.0;
   out_7521593534267777079[269] = 0.0;
   out_7521593534267777079[270] = 0.0;
   out_7521593534267777079[271] = 0.0;
   out_7521593534267777079[272] = 0.0;
   out_7521593534267777079[273] = 0.0;
   out_7521593534267777079[274] = 0.0;
   out_7521593534267777079[275] = 0.0;
   out_7521593534267777079[276] = 0.0;
   out_7521593534267777079[277] = 0.0;
   out_7521593534267777079[278] = 0.0;
   out_7521593534267777079[279] = 0.0;
   out_7521593534267777079[280] = 0.0;
   out_7521593534267777079[281] = 0.0;
   out_7521593534267777079[282] = 0.0;
   out_7521593534267777079[283] = 0.0;
   out_7521593534267777079[284] = 0.0;
   out_7521593534267777079[285] = 1.0;
   out_7521593534267777079[286] = 0.0;
   out_7521593534267777079[287] = 0.0;
   out_7521593534267777079[288] = 0.0;
   out_7521593534267777079[289] = 0.0;
   out_7521593534267777079[290] = 0.0;
   out_7521593534267777079[291] = 0.0;
   out_7521593534267777079[292] = 0.0;
   out_7521593534267777079[293] = 0.0;
   out_7521593534267777079[294] = 0.0;
   out_7521593534267777079[295] = 0.0;
   out_7521593534267777079[296] = 0.0;
   out_7521593534267777079[297] = 0.0;
   out_7521593534267777079[298] = 0.0;
   out_7521593534267777079[299] = 0.0;
   out_7521593534267777079[300] = 0.0;
   out_7521593534267777079[301] = 0.0;
   out_7521593534267777079[302] = 0.0;
   out_7521593534267777079[303] = 0.0;
   out_7521593534267777079[304] = 1.0;
   out_7521593534267777079[305] = 0.0;
   out_7521593534267777079[306] = 0.0;
   out_7521593534267777079[307] = 0.0;
   out_7521593534267777079[308] = 0.0;
   out_7521593534267777079[309] = 0.0;
   out_7521593534267777079[310] = 0.0;
   out_7521593534267777079[311] = 0.0;
   out_7521593534267777079[312] = 0.0;
   out_7521593534267777079[313] = 0.0;
   out_7521593534267777079[314] = 0.0;
   out_7521593534267777079[315] = 0.0;
   out_7521593534267777079[316] = 0.0;
   out_7521593534267777079[317] = 0.0;
   out_7521593534267777079[318] = 0.0;
   out_7521593534267777079[319] = 0.0;
   out_7521593534267777079[320] = 0.0;
   out_7521593534267777079[321] = 0.0;
   out_7521593534267777079[322] = 0.0;
   out_7521593534267777079[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8190127916652503129) {
   out_8190127916652503129[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8190127916652503129[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8190127916652503129[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8190127916652503129[3] = dt*state[12] + state[3];
   out_8190127916652503129[4] = dt*state[13] + state[4];
   out_8190127916652503129[5] = dt*state[14] + state[5];
   out_8190127916652503129[6] = state[6];
   out_8190127916652503129[7] = state[7];
   out_8190127916652503129[8] = state[8];
   out_8190127916652503129[9] = state[9];
   out_8190127916652503129[10] = state[10];
   out_8190127916652503129[11] = state[11];
   out_8190127916652503129[12] = state[12];
   out_8190127916652503129[13] = state[13];
   out_8190127916652503129[14] = state[14];
   out_8190127916652503129[15] = state[15];
   out_8190127916652503129[16] = state[16];
   out_8190127916652503129[17] = state[17];
}
void F_fun(double *state, double dt, double *out_8302830792992532360) {
   out_8302830792992532360[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8302830792992532360[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8302830792992532360[2] = 0;
   out_8302830792992532360[3] = 0;
   out_8302830792992532360[4] = 0;
   out_8302830792992532360[5] = 0;
   out_8302830792992532360[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8302830792992532360[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8302830792992532360[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8302830792992532360[9] = 0;
   out_8302830792992532360[10] = 0;
   out_8302830792992532360[11] = 0;
   out_8302830792992532360[12] = 0;
   out_8302830792992532360[13] = 0;
   out_8302830792992532360[14] = 0;
   out_8302830792992532360[15] = 0;
   out_8302830792992532360[16] = 0;
   out_8302830792992532360[17] = 0;
   out_8302830792992532360[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8302830792992532360[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8302830792992532360[20] = 0;
   out_8302830792992532360[21] = 0;
   out_8302830792992532360[22] = 0;
   out_8302830792992532360[23] = 0;
   out_8302830792992532360[24] = 0;
   out_8302830792992532360[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8302830792992532360[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8302830792992532360[27] = 0;
   out_8302830792992532360[28] = 0;
   out_8302830792992532360[29] = 0;
   out_8302830792992532360[30] = 0;
   out_8302830792992532360[31] = 0;
   out_8302830792992532360[32] = 0;
   out_8302830792992532360[33] = 0;
   out_8302830792992532360[34] = 0;
   out_8302830792992532360[35] = 0;
   out_8302830792992532360[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8302830792992532360[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8302830792992532360[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8302830792992532360[39] = 0;
   out_8302830792992532360[40] = 0;
   out_8302830792992532360[41] = 0;
   out_8302830792992532360[42] = 0;
   out_8302830792992532360[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8302830792992532360[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8302830792992532360[45] = 0;
   out_8302830792992532360[46] = 0;
   out_8302830792992532360[47] = 0;
   out_8302830792992532360[48] = 0;
   out_8302830792992532360[49] = 0;
   out_8302830792992532360[50] = 0;
   out_8302830792992532360[51] = 0;
   out_8302830792992532360[52] = 0;
   out_8302830792992532360[53] = 0;
   out_8302830792992532360[54] = 0;
   out_8302830792992532360[55] = 0;
   out_8302830792992532360[56] = 0;
   out_8302830792992532360[57] = 1;
   out_8302830792992532360[58] = 0;
   out_8302830792992532360[59] = 0;
   out_8302830792992532360[60] = 0;
   out_8302830792992532360[61] = 0;
   out_8302830792992532360[62] = 0;
   out_8302830792992532360[63] = 0;
   out_8302830792992532360[64] = 0;
   out_8302830792992532360[65] = 0;
   out_8302830792992532360[66] = dt;
   out_8302830792992532360[67] = 0;
   out_8302830792992532360[68] = 0;
   out_8302830792992532360[69] = 0;
   out_8302830792992532360[70] = 0;
   out_8302830792992532360[71] = 0;
   out_8302830792992532360[72] = 0;
   out_8302830792992532360[73] = 0;
   out_8302830792992532360[74] = 0;
   out_8302830792992532360[75] = 0;
   out_8302830792992532360[76] = 1;
   out_8302830792992532360[77] = 0;
   out_8302830792992532360[78] = 0;
   out_8302830792992532360[79] = 0;
   out_8302830792992532360[80] = 0;
   out_8302830792992532360[81] = 0;
   out_8302830792992532360[82] = 0;
   out_8302830792992532360[83] = 0;
   out_8302830792992532360[84] = 0;
   out_8302830792992532360[85] = dt;
   out_8302830792992532360[86] = 0;
   out_8302830792992532360[87] = 0;
   out_8302830792992532360[88] = 0;
   out_8302830792992532360[89] = 0;
   out_8302830792992532360[90] = 0;
   out_8302830792992532360[91] = 0;
   out_8302830792992532360[92] = 0;
   out_8302830792992532360[93] = 0;
   out_8302830792992532360[94] = 0;
   out_8302830792992532360[95] = 1;
   out_8302830792992532360[96] = 0;
   out_8302830792992532360[97] = 0;
   out_8302830792992532360[98] = 0;
   out_8302830792992532360[99] = 0;
   out_8302830792992532360[100] = 0;
   out_8302830792992532360[101] = 0;
   out_8302830792992532360[102] = 0;
   out_8302830792992532360[103] = 0;
   out_8302830792992532360[104] = dt;
   out_8302830792992532360[105] = 0;
   out_8302830792992532360[106] = 0;
   out_8302830792992532360[107] = 0;
   out_8302830792992532360[108] = 0;
   out_8302830792992532360[109] = 0;
   out_8302830792992532360[110] = 0;
   out_8302830792992532360[111] = 0;
   out_8302830792992532360[112] = 0;
   out_8302830792992532360[113] = 0;
   out_8302830792992532360[114] = 1;
   out_8302830792992532360[115] = 0;
   out_8302830792992532360[116] = 0;
   out_8302830792992532360[117] = 0;
   out_8302830792992532360[118] = 0;
   out_8302830792992532360[119] = 0;
   out_8302830792992532360[120] = 0;
   out_8302830792992532360[121] = 0;
   out_8302830792992532360[122] = 0;
   out_8302830792992532360[123] = 0;
   out_8302830792992532360[124] = 0;
   out_8302830792992532360[125] = 0;
   out_8302830792992532360[126] = 0;
   out_8302830792992532360[127] = 0;
   out_8302830792992532360[128] = 0;
   out_8302830792992532360[129] = 0;
   out_8302830792992532360[130] = 0;
   out_8302830792992532360[131] = 0;
   out_8302830792992532360[132] = 0;
   out_8302830792992532360[133] = 1;
   out_8302830792992532360[134] = 0;
   out_8302830792992532360[135] = 0;
   out_8302830792992532360[136] = 0;
   out_8302830792992532360[137] = 0;
   out_8302830792992532360[138] = 0;
   out_8302830792992532360[139] = 0;
   out_8302830792992532360[140] = 0;
   out_8302830792992532360[141] = 0;
   out_8302830792992532360[142] = 0;
   out_8302830792992532360[143] = 0;
   out_8302830792992532360[144] = 0;
   out_8302830792992532360[145] = 0;
   out_8302830792992532360[146] = 0;
   out_8302830792992532360[147] = 0;
   out_8302830792992532360[148] = 0;
   out_8302830792992532360[149] = 0;
   out_8302830792992532360[150] = 0;
   out_8302830792992532360[151] = 0;
   out_8302830792992532360[152] = 1;
   out_8302830792992532360[153] = 0;
   out_8302830792992532360[154] = 0;
   out_8302830792992532360[155] = 0;
   out_8302830792992532360[156] = 0;
   out_8302830792992532360[157] = 0;
   out_8302830792992532360[158] = 0;
   out_8302830792992532360[159] = 0;
   out_8302830792992532360[160] = 0;
   out_8302830792992532360[161] = 0;
   out_8302830792992532360[162] = 0;
   out_8302830792992532360[163] = 0;
   out_8302830792992532360[164] = 0;
   out_8302830792992532360[165] = 0;
   out_8302830792992532360[166] = 0;
   out_8302830792992532360[167] = 0;
   out_8302830792992532360[168] = 0;
   out_8302830792992532360[169] = 0;
   out_8302830792992532360[170] = 0;
   out_8302830792992532360[171] = 1;
   out_8302830792992532360[172] = 0;
   out_8302830792992532360[173] = 0;
   out_8302830792992532360[174] = 0;
   out_8302830792992532360[175] = 0;
   out_8302830792992532360[176] = 0;
   out_8302830792992532360[177] = 0;
   out_8302830792992532360[178] = 0;
   out_8302830792992532360[179] = 0;
   out_8302830792992532360[180] = 0;
   out_8302830792992532360[181] = 0;
   out_8302830792992532360[182] = 0;
   out_8302830792992532360[183] = 0;
   out_8302830792992532360[184] = 0;
   out_8302830792992532360[185] = 0;
   out_8302830792992532360[186] = 0;
   out_8302830792992532360[187] = 0;
   out_8302830792992532360[188] = 0;
   out_8302830792992532360[189] = 0;
   out_8302830792992532360[190] = 1;
   out_8302830792992532360[191] = 0;
   out_8302830792992532360[192] = 0;
   out_8302830792992532360[193] = 0;
   out_8302830792992532360[194] = 0;
   out_8302830792992532360[195] = 0;
   out_8302830792992532360[196] = 0;
   out_8302830792992532360[197] = 0;
   out_8302830792992532360[198] = 0;
   out_8302830792992532360[199] = 0;
   out_8302830792992532360[200] = 0;
   out_8302830792992532360[201] = 0;
   out_8302830792992532360[202] = 0;
   out_8302830792992532360[203] = 0;
   out_8302830792992532360[204] = 0;
   out_8302830792992532360[205] = 0;
   out_8302830792992532360[206] = 0;
   out_8302830792992532360[207] = 0;
   out_8302830792992532360[208] = 0;
   out_8302830792992532360[209] = 1;
   out_8302830792992532360[210] = 0;
   out_8302830792992532360[211] = 0;
   out_8302830792992532360[212] = 0;
   out_8302830792992532360[213] = 0;
   out_8302830792992532360[214] = 0;
   out_8302830792992532360[215] = 0;
   out_8302830792992532360[216] = 0;
   out_8302830792992532360[217] = 0;
   out_8302830792992532360[218] = 0;
   out_8302830792992532360[219] = 0;
   out_8302830792992532360[220] = 0;
   out_8302830792992532360[221] = 0;
   out_8302830792992532360[222] = 0;
   out_8302830792992532360[223] = 0;
   out_8302830792992532360[224] = 0;
   out_8302830792992532360[225] = 0;
   out_8302830792992532360[226] = 0;
   out_8302830792992532360[227] = 0;
   out_8302830792992532360[228] = 1;
   out_8302830792992532360[229] = 0;
   out_8302830792992532360[230] = 0;
   out_8302830792992532360[231] = 0;
   out_8302830792992532360[232] = 0;
   out_8302830792992532360[233] = 0;
   out_8302830792992532360[234] = 0;
   out_8302830792992532360[235] = 0;
   out_8302830792992532360[236] = 0;
   out_8302830792992532360[237] = 0;
   out_8302830792992532360[238] = 0;
   out_8302830792992532360[239] = 0;
   out_8302830792992532360[240] = 0;
   out_8302830792992532360[241] = 0;
   out_8302830792992532360[242] = 0;
   out_8302830792992532360[243] = 0;
   out_8302830792992532360[244] = 0;
   out_8302830792992532360[245] = 0;
   out_8302830792992532360[246] = 0;
   out_8302830792992532360[247] = 1;
   out_8302830792992532360[248] = 0;
   out_8302830792992532360[249] = 0;
   out_8302830792992532360[250] = 0;
   out_8302830792992532360[251] = 0;
   out_8302830792992532360[252] = 0;
   out_8302830792992532360[253] = 0;
   out_8302830792992532360[254] = 0;
   out_8302830792992532360[255] = 0;
   out_8302830792992532360[256] = 0;
   out_8302830792992532360[257] = 0;
   out_8302830792992532360[258] = 0;
   out_8302830792992532360[259] = 0;
   out_8302830792992532360[260] = 0;
   out_8302830792992532360[261] = 0;
   out_8302830792992532360[262] = 0;
   out_8302830792992532360[263] = 0;
   out_8302830792992532360[264] = 0;
   out_8302830792992532360[265] = 0;
   out_8302830792992532360[266] = 1;
   out_8302830792992532360[267] = 0;
   out_8302830792992532360[268] = 0;
   out_8302830792992532360[269] = 0;
   out_8302830792992532360[270] = 0;
   out_8302830792992532360[271] = 0;
   out_8302830792992532360[272] = 0;
   out_8302830792992532360[273] = 0;
   out_8302830792992532360[274] = 0;
   out_8302830792992532360[275] = 0;
   out_8302830792992532360[276] = 0;
   out_8302830792992532360[277] = 0;
   out_8302830792992532360[278] = 0;
   out_8302830792992532360[279] = 0;
   out_8302830792992532360[280] = 0;
   out_8302830792992532360[281] = 0;
   out_8302830792992532360[282] = 0;
   out_8302830792992532360[283] = 0;
   out_8302830792992532360[284] = 0;
   out_8302830792992532360[285] = 1;
   out_8302830792992532360[286] = 0;
   out_8302830792992532360[287] = 0;
   out_8302830792992532360[288] = 0;
   out_8302830792992532360[289] = 0;
   out_8302830792992532360[290] = 0;
   out_8302830792992532360[291] = 0;
   out_8302830792992532360[292] = 0;
   out_8302830792992532360[293] = 0;
   out_8302830792992532360[294] = 0;
   out_8302830792992532360[295] = 0;
   out_8302830792992532360[296] = 0;
   out_8302830792992532360[297] = 0;
   out_8302830792992532360[298] = 0;
   out_8302830792992532360[299] = 0;
   out_8302830792992532360[300] = 0;
   out_8302830792992532360[301] = 0;
   out_8302830792992532360[302] = 0;
   out_8302830792992532360[303] = 0;
   out_8302830792992532360[304] = 1;
   out_8302830792992532360[305] = 0;
   out_8302830792992532360[306] = 0;
   out_8302830792992532360[307] = 0;
   out_8302830792992532360[308] = 0;
   out_8302830792992532360[309] = 0;
   out_8302830792992532360[310] = 0;
   out_8302830792992532360[311] = 0;
   out_8302830792992532360[312] = 0;
   out_8302830792992532360[313] = 0;
   out_8302830792992532360[314] = 0;
   out_8302830792992532360[315] = 0;
   out_8302830792992532360[316] = 0;
   out_8302830792992532360[317] = 0;
   out_8302830792992532360[318] = 0;
   out_8302830792992532360[319] = 0;
   out_8302830792992532360[320] = 0;
   out_8302830792992532360[321] = 0;
   out_8302830792992532360[322] = 0;
   out_8302830792992532360[323] = 1;
}
void h_4(double *state, double *unused, double *out_6664200415740758039) {
   out_6664200415740758039[0] = state[6] + state[9];
   out_6664200415740758039[1] = state[7] + state[10];
   out_6664200415740758039[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_5772632154402693802) {
   out_5772632154402693802[0] = 0;
   out_5772632154402693802[1] = 0;
   out_5772632154402693802[2] = 0;
   out_5772632154402693802[3] = 0;
   out_5772632154402693802[4] = 0;
   out_5772632154402693802[5] = 0;
   out_5772632154402693802[6] = 1;
   out_5772632154402693802[7] = 0;
   out_5772632154402693802[8] = 0;
   out_5772632154402693802[9] = 1;
   out_5772632154402693802[10] = 0;
   out_5772632154402693802[11] = 0;
   out_5772632154402693802[12] = 0;
   out_5772632154402693802[13] = 0;
   out_5772632154402693802[14] = 0;
   out_5772632154402693802[15] = 0;
   out_5772632154402693802[16] = 0;
   out_5772632154402693802[17] = 0;
   out_5772632154402693802[18] = 0;
   out_5772632154402693802[19] = 0;
   out_5772632154402693802[20] = 0;
   out_5772632154402693802[21] = 0;
   out_5772632154402693802[22] = 0;
   out_5772632154402693802[23] = 0;
   out_5772632154402693802[24] = 0;
   out_5772632154402693802[25] = 1;
   out_5772632154402693802[26] = 0;
   out_5772632154402693802[27] = 0;
   out_5772632154402693802[28] = 1;
   out_5772632154402693802[29] = 0;
   out_5772632154402693802[30] = 0;
   out_5772632154402693802[31] = 0;
   out_5772632154402693802[32] = 0;
   out_5772632154402693802[33] = 0;
   out_5772632154402693802[34] = 0;
   out_5772632154402693802[35] = 0;
   out_5772632154402693802[36] = 0;
   out_5772632154402693802[37] = 0;
   out_5772632154402693802[38] = 0;
   out_5772632154402693802[39] = 0;
   out_5772632154402693802[40] = 0;
   out_5772632154402693802[41] = 0;
   out_5772632154402693802[42] = 0;
   out_5772632154402693802[43] = 0;
   out_5772632154402693802[44] = 1;
   out_5772632154402693802[45] = 0;
   out_5772632154402693802[46] = 0;
   out_5772632154402693802[47] = 1;
   out_5772632154402693802[48] = 0;
   out_5772632154402693802[49] = 0;
   out_5772632154402693802[50] = 0;
   out_5772632154402693802[51] = 0;
   out_5772632154402693802[52] = 0;
   out_5772632154402693802[53] = 0;
}
void h_10(double *state, double *unused, double *out_2232580687525306632) {
   out_2232580687525306632[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_2232580687525306632[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_2232580687525306632[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_1994505413045679835) {
   out_1994505413045679835[0] = 0;
   out_1994505413045679835[1] = 9.8100000000000005*cos(state[1]);
   out_1994505413045679835[2] = 0;
   out_1994505413045679835[3] = 0;
   out_1994505413045679835[4] = -state[8];
   out_1994505413045679835[5] = state[7];
   out_1994505413045679835[6] = 0;
   out_1994505413045679835[7] = state[5];
   out_1994505413045679835[8] = -state[4];
   out_1994505413045679835[9] = 0;
   out_1994505413045679835[10] = 0;
   out_1994505413045679835[11] = 0;
   out_1994505413045679835[12] = 1;
   out_1994505413045679835[13] = 0;
   out_1994505413045679835[14] = 0;
   out_1994505413045679835[15] = 1;
   out_1994505413045679835[16] = 0;
   out_1994505413045679835[17] = 0;
   out_1994505413045679835[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_1994505413045679835[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_1994505413045679835[20] = 0;
   out_1994505413045679835[21] = state[8];
   out_1994505413045679835[22] = 0;
   out_1994505413045679835[23] = -state[6];
   out_1994505413045679835[24] = -state[5];
   out_1994505413045679835[25] = 0;
   out_1994505413045679835[26] = state[3];
   out_1994505413045679835[27] = 0;
   out_1994505413045679835[28] = 0;
   out_1994505413045679835[29] = 0;
   out_1994505413045679835[30] = 0;
   out_1994505413045679835[31] = 1;
   out_1994505413045679835[32] = 0;
   out_1994505413045679835[33] = 0;
   out_1994505413045679835[34] = 1;
   out_1994505413045679835[35] = 0;
   out_1994505413045679835[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_1994505413045679835[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_1994505413045679835[38] = 0;
   out_1994505413045679835[39] = -state[7];
   out_1994505413045679835[40] = state[6];
   out_1994505413045679835[41] = 0;
   out_1994505413045679835[42] = state[4];
   out_1994505413045679835[43] = -state[3];
   out_1994505413045679835[44] = 0;
   out_1994505413045679835[45] = 0;
   out_1994505413045679835[46] = 0;
   out_1994505413045679835[47] = 0;
   out_1994505413045679835[48] = 0;
   out_1994505413045679835[49] = 0;
   out_1994505413045679835[50] = 1;
   out_1994505413045679835[51] = 0;
   out_1994505413045679835[52] = 0;
   out_1994505413045679835[53] = 1;
}
void h_13(double *state, double *unused, double *out_1739439411373720736) {
   out_1739439411373720736[0] = state[3];
   out_1739439411373720736[1] = state[4];
   out_1739439411373720736[2] = state[5];
}
void H_13(double *state, double *unused, double *out_2560358329070361001) {
   out_2560358329070361001[0] = 0;
   out_2560358329070361001[1] = 0;
   out_2560358329070361001[2] = 0;
   out_2560358329070361001[3] = 1;
   out_2560358329070361001[4] = 0;
   out_2560358329070361001[5] = 0;
   out_2560358329070361001[6] = 0;
   out_2560358329070361001[7] = 0;
   out_2560358329070361001[8] = 0;
   out_2560358329070361001[9] = 0;
   out_2560358329070361001[10] = 0;
   out_2560358329070361001[11] = 0;
   out_2560358329070361001[12] = 0;
   out_2560358329070361001[13] = 0;
   out_2560358329070361001[14] = 0;
   out_2560358329070361001[15] = 0;
   out_2560358329070361001[16] = 0;
   out_2560358329070361001[17] = 0;
   out_2560358329070361001[18] = 0;
   out_2560358329070361001[19] = 0;
   out_2560358329070361001[20] = 0;
   out_2560358329070361001[21] = 0;
   out_2560358329070361001[22] = 1;
   out_2560358329070361001[23] = 0;
   out_2560358329070361001[24] = 0;
   out_2560358329070361001[25] = 0;
   out_2560358329070361001[26] = 0;
   out_2560358329070361001[27] = 0;
   out_2560358329070361001[28] = 0;
   out_2560358329070361001[29] = 0;
   out_2560358329070361001[30] = 0;
   out_2560358329070361001[31] = 0;
   out_2560358329070361001[32] = 0;
   out_2560358329070361001[33] = 0;
   out_2560358329070361001[34] = 0;
   out_2560358329070361001[35] = 0;
   out_2560358329070361001[36] = 0;
   out_2560358329070361001[37] = 0;
   out_2560358329070361001[38] = 0;
   out_2560358329070361001[39] = 0;
   out_2560358329070361001[40] = 0;
   out_2560358329070361001[41] = 1;
   out_2560358329070361001[42] = 0;
   out_2560358329070361001[43] = 0;
   out_2560358329070361001[44] = 0;
   out_2560358329070361001[45] = 0;
   out_2560358329070361001[46] = 0;
   out_2560358329070361001[47] = 0;
   out_2560358329070361001[48] = 0;
   out_2560358329070361001[49] = 0;
   out_2560358329070361001[50] = 0;
   out_2560358329070361001[51] = 0;
   out_2560358329070361001[52] = 0;
   out_2560358329070361001[53] = 0;
}
void h_14(double *state, double *unused, double *out_2162487226046509469) {
   out_2162487226046509469[0] = state[6];
   out_2162487226046509469[1] = state[7];
   out_2162487226046509469[2] = state[8];
}
void H_14(double *state, double *unused, double *out_1809391298063209273) {
   out_1809391298063209273[0] = 0;
   out_1809391298063209273[1] = 0;
   out_1809391298063209273[2] = 0;
   out_1809391298063209273[3] = 0;
   out_1809391298063209273[4] = 0;
   out_1809391298063209273[5] = 0;
   out_1809391298063209273[6] = 1;
   out_1809391298063209273[7] = 0;
   out_1809391298063209273[8] = 0;
   out_1809391298063209273[9] = 0;
   out_1809391298063209273[10] = 0;
   out_1809391298063209273[11] = 0;
   out_1809391298063209273[12] = 0;
   out_1809391298063209273[13] = 0;
   out_1809391298063209273[14] = 0;
   out_1809391298063209273[15] = 0;
   out_1809391298063209273[16] = 0;
   out_1809391298063209273[17] = 0;
   out_1809391298063209273[18] = 0;
   out_1809391298063209273[19] = 0;
   out_1809391298063209273[20] = 0;
   out_1809391298063209273[21] = 0;
   out_1809391298063209273[22] = 0;
   out_1809391298063209273[23] = 0;
   out_1809391298063209273[24] = 0;
   out_1809391298063209273[25] = 1;
   out_1809391298063209273[26] = 0;
   out_1809391298063209273[27] = 0;
   out_1809391298063209273[28] = 0;
   out_1809391298063209273[29] = 0;
   out_1809391298063209273[30] = 0;
   out_1809391298063209273[31] = 0;
   out_1809391298063209273[32] = 0;
   out_1809391298063209273[33] = 0;
   out_1809391298063209273[34] = 0;
   out_1809391298063209273[35] = 0;
   out_1809391298063209273[36] = 0;
   out_1809391298063209273[37] = 0;
   out_1809391298063209273[38] = 0;
   out_1809391298063209273[39] = 0;
   out_1809391298063209273[40] = 0;
   out_1809391298063209273[41] = 0;
   out_1809391298063209273[42] = 0;
   out_1809391298063209273[43] = 0;
   out_1809391298063209273[44] = 1;
   out_1809391298063209273[45] = 0;
   out_1809391298063209273[46] = 0;
   out_1809391298063209273[47] = 0;
   out_1809391298063209273[48] = 0;
   out_1809391298063209273[49] = 0;
   out_1809391298063209273[50] = 0;
   out_1809391298063209273[51] = 0;
   out_1809391298063209273[52] = 0;
   out_1809391298063209273[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_8386835163844872263) {
  err_fun(nom_x, delta_x, out_8386835163844872263);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_5826204590882848019) {
  inv_err_fun(nom_x, true_x, out_5826204590882848019);
}
void pose_H_mod_fun(double *state, double *out_7521593534267777079) {
  H_mod_fun(state, out_7521593534267777079);
}
void pose_f_fun(double *state, double dt, double *out_8190127916652503129) {
  f_fun(state,  dt, out_8190127916652503129);
}
void pose_F_fun(double *state, double dt, double *out_8302830792992532360) {
  F_fun(state,  dt, out_8302830792992532360);
}
void pose_h_4(double *state, double *unused, double *out_6664200415740758039) {
  h_4(state, unused, out_6664200415740758039);
}
void pose_H_4(double *state, double *unused, double *out_5772632154402693802) {
  H_4(state, unused, out_5772632154402693802);
}
void pose_h_10(double *state, double *unused, double *out_2232580687525306632) {
  h_10(state, unused, out_2232580687525306632);
}
void pose_H_10(double *state, double *unused, double *out_1994505413045679835) {
  H_10(state, unused, out_1994505413045679835);
}
void pose_h_13(double *state, double *unused, double *out_1739439411373720736) {
  h_13(state, unused, out_1739439411373720736);
}
void pose_H_13(double *state, double *unused, double *out_2560358329070361001) {
  H_13(state, unused, out_2560358329070361001);
}
void pose_h_14(double *state, double *unused, double *out_2162487226046509469) {
  h_14(state, unused, out_2162487226046509469);
}
void pose_H_14(double *state, double *unused, double *out_1809391298063209273) {
  H_14(state, unused, out_1809391298063209273);
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
